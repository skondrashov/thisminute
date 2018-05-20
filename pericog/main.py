#!/usr/bin/python
from __future__ import print_function
from __future__ import division
print("Importing...")
import sys, os

import logging, time

sys.path.append(os.path.abspath('/srv/lib/'))
from util import get_words, db_tweets_connect, config

from model import Model

pericog = Model.factory('pericog', 'pericog')
pericog.load_and_train()

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

print("Connecting to self")
db_pericog_connection = db_tweets_connect('pericog', 'localhost')
db_pericog_cursor = db_pericog_connection.cursor()

print("Connecting to tweets")
ACTIVE_DB_NAME = config('connections', 'active')
db_tweets_connection = db_tweets_connect('pericog', config('connections', ACTIVE_DB_NAME))
db_tweets_cursor = db_tweets_connection.cursor()

last_runtime = time.time()
while True:
	db_tweets_cursor.execute("SELECT EXTRACT(EPOCH FROM MAX(time)) FROM tweets")
	for timestamp, in db_tweets_cursor.fetchall():
		current_time = timestamp - 1

	print("Getting last %s seconds of tweets" % str(current_time - last_runtime))
	db_tweets_cursor.execute("""
			SELECT
				id,
				time,
				ST_AsText(geo) AS geolocation,
				exact,
				user,
				text
			FROM tweets
			WHERE TO_TIMESTAMP(%s) <= time AND time < TO_TIMESTAMP(%s)
			ORDER BY time ASC
		""", (last_runtime, current_time))

	last_runtime = current_time

	X = []
	for id, timestamp, geolocation, exact, user, text in db_tweets_cursor.fetchall():
		if not get_words(text):
			continue

		X.append(text)

	db_tweets_connection.commit()

	if X:
		Y = pericog.predict(X)

		print("Positives:")
		for row in zip(X,Y):
			if row[1]:
				print(row[0])

		print("Negatives:")
		for row in zip(X,Y):
			if not row[1]:
				print(row[0])


	time.sleep(1)
