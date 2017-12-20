#!/usr/bin/python
from __future__ import print_function
from __future__ import division

import numpy
import tensorflow

from gensim.models import Doc2Vec
from gensim.models.doc2vec import TaggedDocument

from tensorflow.python.estimator.inputs import numpy_io

import logging, time

import ConfigParser
import mysql.connector

import sys
import os
sys.path.append(os.path.abspath('/srv/lib/'))

from models import Tweet2Vec, RandomForest

tensorflow.logging.set_verbosity(tensorflow.logging.ERROR)
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

ACTIVE_DB_NAME    = 'tweets-test'#config.get('connections', 'active')
ACTIVE_DB_ADDRESS = config.get('connections', ACTIVE_DB_NAME)

t2v = Tweet2Vec(ACTIVE_DB_NAME, 10000000)
RandomForest.t2v = t2v
rf = RandomForest(ACTIVE_DB_NAME, 10000000)

print("Connecting to ", ACTIVE_DB_NAME, " at ", ACTIVE_DB_ADDRESS)
db_tweets_connection = mysql.connector.connect(
		user='pericog',
		password=open('/srv/auth/mysql/pericog.pw').read(),
		host=ACTIVE_DB_ADDRESS,
		database='ThisMinute'
	)
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

	documents = []
	X = []
	for id, timestamp, lon, lat, exact, user, text in db_tweets_cursor.fetchall():
		if not get_words(text):
			continue

		documents.append(text)
		X.append(t2v.get_vector(text).tolist())
	if not X:
		continue

	X = rf.preprocess_x(X)
	Y = rf.predict(X)

	for i, prediction in enumerate(Y):
		print(prediction['logistic'][0], "\t", documents[i])
