#!/usr/bin/python
from __future__ import print_function
from __future__ import division

import numpy
import tensorflow

from gensim.models import Doc2Vec
from gensim.models.doc2vec import TaggedDocument

from tensorflow.contrib.tensor_forest.client import random_forest
from tensorflow.contrib.tensor_forest.python import tensor_forest
from tensorflow.python.estimator.inputs import numpy_io

from tensorflow.contrib.learn.python.learn import metric_spec
from tensorflow.contrib.tensor_forest.client import eval_metrics

import logging, time

import ConfigParser
import psycopg2 as sql

import sys
import os

sys.path.append(os.path.abspath('/srv/lib/'))
from util import db_tweets_connect
from models import Tweet2Vec, RandomForest

tensorflow.logging.set_verbosity(tensorflow.logging.ERROR)
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

ACTIVE_DB_NAME    = config.get('connections', 'active')
ACTIVE_DB_ADDRESS = config.get('connections', ACTIVE_DB_NAME)
print("Connecting to ", ACTIVE_DB_NAME, " at ", ACTIVE_DB_ADDRESS)
db_tweets_connection = db_tweets_connect('pericog', ACTIVE_DB_ADDRESS)
db_tweets_cursor = db_tweets_connection.cursor()

t2v = Tweet2Vec(db_tweets_cursor, {
		{
			'string':'legible=TRUE',
			'limit': 10000
		}
	})
RandomForest.t2v = t2v
rf = RandomForest(db_tweets_cursor, {
		{
			'string':'informative=TRUE',
			'limit': 10000
		},
		{
			'string':'informative=FALSE',
			'limit': 10000
		}
	})

last_runtime = time.time()
while True:
	db_tweets_connection.commit()

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
		X.append(get_vector(text).tolist())
	if not X:
		continue

	X = numpy.array(X).astype(numpy.float32)
	Y = rf.predict(
			input_fn=numpy_io.numpy_input_fn(
				x={'features': X},
				batch_size=1000,
				num_epochs=1,
				shuffle=False
			)
		)

	for i, prediction in enumerate(Y):
		print(prediction['logistic'][0], "\t", documents[i])
