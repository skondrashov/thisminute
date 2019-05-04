#!/usr/bin/python
from __future__ import print_function
from __future__ import division
print("Importing modules for pericog")
import sys, os

import csv
import logging, time

sys.path.append(os.path.abspath('/srv/lib/'))
from util import get_words, db_tweets_connect, config

print("Connecting to tweets")
ACTIVE_DB_NAME = config('connections', 'active')
db_tweets_connection = db_tweets_connect('pericog', config('connections', ACTIVE_DB_NAME))
db_tweets_cursor = db_tweets_connection.cursor()

db_tweets_cursor.execute("""
		SELECT
			id, text
		FROM tweets
		LEFT JOIN tweet_properties ON id = tweet_id
		WHERE
			crowdflower IS NOT NULL
	""")

with open('somefile.csv', 'w') as f:
	writer = csv.writer(f, delimiter=',')
	for row in db_tweets_cursor.fetchall():
		writer.writerow([unicode(s).encode("utf-8") for s in row])
