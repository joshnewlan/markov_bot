import requests
from requests.auth import HTTPBasicAuth
import markovify
import time
import sys

"""
Usage:
$ python markov_bot.py
or
$ python markov_bot.py --loop

Add the --loop argument to run the script as a while loop that checks for new 
mentions every minute.

Otherwise the script checks for new mentions and comments once and replies.

"""

# Define some globals
client_auth = HTTPBasicAuth('CLIENT_ID', 'CLIENT_SECRET')
headers = {"User-Agent": "BOT_NAME/0.1 by /u/USER"}
post_data = {
    "grant_type": "password",
    "username": "BOT_USERNAME", 
    "password": "PASSWORD"
    }

# A newline delimited text file
markov_model_file = '/path/to/markov_file.txt'
# A checkpoint file to avoid responding to mentions twice
mentions_checkpoint = '/path/to/mentions.txt'
# Used to check if we need to get a new auth token
token_time = time.time()

def authenticate():
    # Collect new access_token
    response = requests.post("https://www.reddit.com/api/v1/access_token",
        auth=client_auth, data=post_data, headers=headers)
    token = response.json()['access_token']
    token_time = time.time()
    return token

def authenticated_request(url, token):
    # Make an authenticated get request using an access_token
    headers["Authorization"] = "bearer %s" % token
    if int(time.time() - token_time) < 3600:
        try:
            # Try with token
            response = requests.get("https://oauth.reddit.com/%s" % (url),
                headers=headers)
        except Exception, e:
            print "Error: ", e
    else:
        # Get a new token
        token = authenticate()
        headers["Authorization"] = "bearer %s" % token
        try:
            # Try again with new token
            response = requests.get("https://oauth.reddit.com/%s" % (url),
                headers=headers)
        except Exception, e:
            print "Error: ", e
    return response

def initialize_model(text_file):
    # Load markovify model with a text file filepath
    with open('%s' % (text_file)) as f:
        text = f.read()
    text_model = markovify.Text(text)
    return text_model

def generate_statement(text_model):
    comment = ""
    for i in range(3):
        sentence = text_model.make_short_sentence(140)
        comment += " " + sentence
    return comment

def check_mail(token):
    # Returns a boolean. True if unread mail exists.
    me = authenticated_request("api/v1/me", token)
    return me.json()['has_mail']

def get_comments_and_mentions(token):
    # Returns all comments and mentions data
    mentions = authenticated_request("message/mentions.json",token)
    data = mentions.json()['data']['children']
    time.sleep(1)
    comments = authenticated_request("message/comments.json",token)
    data += comments.json()['data']['children']
    return data

def process_mentions(mentions_data):
    # Returns a list of comment ids to reply to or and empty list 
    # Appends new ids to previously replied file.

    comment_mentions = []
    with open(mentions_checkpoint,'r') as f:
        previous_mentions = f.read().splitlines()
    print "Previous comments and mentions: ", previous_mentions
    
    mention_ids = [child['data']['id'] for child in mentions_data 
        if child['data']['was_comment'] == True and
        child['data']['id'] not in previous_mentions]

    print "New mentions: ", mention_ids
    
    for mention in mention_ids:
        with open(mentions_checkpoint, "a") as f:
            f.write(mention + "\n")
        comment_mentions.append(mention)
    return comment_mentions

def reply_to_mentions(comment_mentions,text_model):
    # Takes a list of comment thing_ids. 
    # Prepends the thing code (t1) and comments as the authenticated user
    if int(time.time() - token_time) > 3600:
        token = authenticate()
        headers["Authorization"] = "bearer %s" % token

    for mention in comment_mentions:
        requests.post('https://oauth.reddit.com/api/comment',
            data={'parent':'t1_%s' % (mention),
                'text': generate_statement(text_model)},
            headers=headers)
            print "Replied to %s" % mention
        time.sleep(1)

def mark_as_read(token):
    # Successful response code from post is 202.
    # If 429 received, request rate has exceeded api limits 
    if int(time.time() - token_time) > 3600:
        token = authenticate()
        headers["Authorization"] = "bearer %s" % token

    r = requests.post('https://oauth.reddit.com/api/read_all_messages',
        headers=headers)

    if int(r.status_code) == 202:
        while check_mail(token) == True:
            print "Waiting until unread messages are cleared"
            time.sleep(1)
        print "Unread messages removed"
    elif int(r.status_code) == 429:
        print r.headers
        print "Rate limited, please wait 60 seconds"
        time.sleep(60)
        mark_as_read(token)

def run_mark_loop(text_model):
    token = authenticate()
    while True:
        if check_mail(token):
            all_coms_and_mentions = get_comments_and_mentions(token)
            reply_mentions = process_mentions(all_coms_and_mentions)
            if len(reply_mentions) > 0:
                reply_to_mentions(reply_mentions,text_model)
            mark_as_read(token)
        else:
            print "Nothing found, sleeping for 60 seconds"
            time.sleep(60)

def run_mark(text_model):
    token = authenticate()
    if check_mail(token):
        all_coms_and_mentions = get_comments_and_mentions(token)
        reply_mentions = process_mentions(all_coms_and_mentions)
        if len(reply_mentions) > 0:
            reply_to_mentions(reply_mentions,text_model)
        mark_as_read(token)
    else:
        print "No new comments or mentions found."

def main():
    text_model = initialize_model(markov_model_file)
    if len(sys.argv) == 2 and sys.argv[1] == '--loop':
        run_mark_loop(text_model)
    else:
        run_mark(text_model)

if __name__ == '__main__':
    main()
