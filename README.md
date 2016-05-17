# markov_bot
A python reddit bot for responding to mentions or comments with a markov chain sentence.
Relies on Markovify.

### Usage
```
$ python markov_bot.py
or
$ python markov_bot.py --loop
```
Add the --loop argument to run the script as a while loop that checks for new 
mentions every minute.

Otherwise the script checks for new mentions and comments once and replies.

