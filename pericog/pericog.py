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
import mysql.connector

import re
from unidecode import unidecode
import os.path

tensorflow.logging.set_verbosity(tensorflow.logging.ERROR)
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

print("Connecting to self")
db_pericog_connection = mysql.connector.connect(
		user='pericog',
		password=open('/srv/auth/mysql/pericog.pw').read(),
		host='localhost',
		database='ThisMinute'
	)
db_pericog_cursor = db_pericog_connection.cursor()

print("Connecting to tweets")
ACTIVE_DB_NAME = config.get('connections', 'active')
db_tweets_connection = mysql.connector.connect(
		user='pericog',
		password=open('/srv/auth/mysql/pericog.pw').read(),
		host=config.get('connections', ACTIVE_DB_NAME),
		database='ThisMinute'
	)
db_tweets_cursor = db_tweets_connection.cursor()

def get_words(tweet):
	tweet = re.sub('((\B@)|(\\bhttps?:\/\/))[^\\s]+', " ", tweet)
	tweet = re.sub('[^\w]+', " ", tweet)
	tweet = tweet.lower().strip()
	tweet = unicode(unidecode(tweet))
	return tweet.split()

def get_vector(tweet):
	return t2v.infer_vector(get_words(tweet), alpha=0.1, min_alpha=0.0001, steps=5)

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

t2v = load_model(
		'tweet2vec',
		lambda path: Doc2Vec.load(path),
		lambda X: [TaggedDocument(get_words(tweet), [category]) for category, tweet in zip(load_model.X, load_model.Y)],
		lambda Y: Y,
		lambda model, X, Y: Doc2Vec(
				dm=1, dbow_words=1, dm_mean=0, dm_concat=0, dm_tag_count=1,
				hs=1,
				negative=0,

				size=int(config.get('tweet2vec', 'vector_size')),
				alpha=0.025,
				window=8,
				min_count=0,
				sample=1e-4,
				iter=10,

				max_vocab_size=None,
				workers=int(config.get('tweet2vec', 'thread_count')),
				batch_words=1000000,
				min_alpha=0.0001,
				seed=1,

				### no documentation ###
				# docvecs=None,
				# docvecs_mapfile='',
				# trim_rule=None,
				# comment=None,

				documents=X,
			),
		10000,
		False
	)

rf_estimator = load_model(
		'random_forest',
		lambda path: random_forest.TensorForestEstimator(
				tensor_forest.ForestHParams(
						num_classes=2,
						num_features=784,
						num_trees=100,
						max_nodes=1000
					),
				graph_builder_class=tensor_forest.RandomForestGraphs if True else tensor_forest.TrainingLossForest,
				model_dir=path
			),
		lambda X: numpy.array([get_vector(tweet).tolist() for tweet in X]).astype(numpy.float32),
		lambda Y: numpy.array(Y).astype(numpy.float32),
		lambda model, X, Y: model.fit(
				input_fn=numpy_io.numpy_input_fn(
					x={'features': X},
					y=Y,
					batch_size=1000,
					num_epochs=None,
					shuffle=True
				),
				steps=None
			),
		10000,
		True
	)

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
