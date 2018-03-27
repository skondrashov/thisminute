#!/usr/bin/python
from __future__ import print_function
from __future__ import division
import sys, os

import tensorflow

from tensorflow.contrib.learn.python.learn import metric_spec
from tensorflow.contrib.tensor_forest.client import eval_metrics

import logging, time

sys.path.append(os.path.abspath('/srv/lib/'))
from util import get_words, db_tweets_connect, config

from pericog import Pericog

pericog = Pericog(None)

tensorflow.logging.set_verbosity(tensorflow.logging.ERROR)
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
				ST_AsText(the_geom) AS geo,
				exact,
				user,
				text
			FROM tweets
			WHERE TO_TIMESTAMP(%s) <= time AND time < TO_TIMESTAMP(%s)
			ORDER BY time ASC
		""", (last_runtime, current_time))

	last_runtime = current_time

	X = []
	for id, time, geo, exact, user, text in db_tweets_cursor.fetchall():
		if not get_words(text):
			continue

		X.append(text)

	db_tweets_connection.commit()

	if X:
		Y = pericog.predict(X)

	time.sleep(1)


	# for i, prediction in enumerate(Y):
	# 	print(prediction['logistic'][0], "\t", documents[i])
