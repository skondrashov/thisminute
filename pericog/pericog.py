#!/usr/bin/python
from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

import numpy
import tensorflow

from tensorflow.contrib.learn.python.learn import metric_spec
from tensorflow.contrib.tensor_forest.client import eval_metrics

import logging, time

from util import get_words, db_tweets_connect, config
import Model
import Doc2Vec
import Tagger
import Random_Forest

class Pericog(Model):
	def load(self, path):
		print("Loading tweet2vec model")
		self.t2v = Doc2Vec()

		print("Loading random forest model")
		self.rf = Random_Forest()

	def predict(self, X):
		X = [self.t2v.predict(tweet).tolist() for tweet in X]
		X = numpy.array(X).astype(numpy.float32)
		X = self.rf.predict(X)

		return X
pericog = Pericog()

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
	db_tweets_cursor.execute("SELECT UNIX_TIMESTAMP(MAX(time)) FROM tweets")
	for timestamp in db_tweets_cursor.fetchall():
		current_time = timestamp[0] - 1

	print("Getting last %s seconds of tweets" % str(current_time - last_runtime))
	db_tweets_cursor.execute("""
			SELECT *
			FROM tweets
			WHERE FROM_UNIXTIME(%s) <= time AND time < FROM_UNIXTIME(%s)
			ORDER BY time ASC
		""", (last_runtime, current_time))

	last_runtime = current_time

	X = []
	for id, timestamp, lon, lat, exact, user, text in db_tweets_cursor.fetchall():
		if not get_words(text):
			continue

		X.append(text)

	db_tweets_connection.commit()
	Y = pericog.predict(X)

	# for i, prediction in enumerate(Y):
	# 	print(prediction['logistic'][0], "\t", documents[i])
