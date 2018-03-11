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

import sys
import os

sys.path.append(os.path.abspath('/srv/lib/'))
from util import get_words, db_tweets_connect

tensorflow.logging.set_verbosity(tensorflow.logging.ERROR)
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

print("Connecting to self")
db_pericog_connection = db_tweets_connect('pericog', 'localhost')
db_pericog_cursor = db_pericog_connection.cursor()

print("Connecting to tweets")
ACTIVE_DB_NAME = config.get('connections', 'active')
db_tweets_connection = db_tweets_connect('pericog', config.get('connections', ACTIVE_DB_NAME))
db_tweets_cursor = db_tweets_connection.cursor()

def load_model(type, load, preprocess_x, preprocess_y, train, training_size, in_place):
	path = '/srv/' + type + '.model'
	print("Attempting to load model from " + path)
	try:
		model = load(path)
	except:
		pass

	if os.path.isfile(path):
		return model
	print("No model found at " + path)

	print("Loading tweets to train new model")
	for category in [True, False]:
		db_tweets_cursor.execute("""
				SELECT
					tweet_id,
					text
				FROM training_tweets
				WHERE
					frantic = %s OR 1=1
				LIMIT %s
			""", (category, training_size - len(load_model.X)))
		for id, text in db_tweets_cursor.fetchall():
			if not get_words(text):
				continue

			load_model.X.append(text)
			load_model.Y.append(category)

	print("Training new model")
	temp = train(model, preprocess_x(load_model.X), preprocess_y(load_model.Y))
	if not in_place:
		model = temp

	return model
load_model.X = []
load_model.Y = []

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
	Y = rf_estimator.predict(
			input_fn=numpy_io.numpy_input_fn(
				x={'features': X},
				batch_size=1000,
				num_epochs=1,
				shuffle=False
			)
		)

	for i, prediction in enumerate(Y):
		print(prediction['logistic'][0], "\t", documents[i])
