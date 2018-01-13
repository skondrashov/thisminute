from __future__ import print_function
from __future__ import division

from collections import defaultdict
import numpy

from gensim.models import Doc2Vec
from gensim.models.doc2vec import TaggedDocument

from tensorflow.contrib.tensor_forest.client import random_forest
from tensorflow.contrib.tensor_forest.python import tensor_forest
from tensorflow.python.estimator.inputs import numpy_io

import os
import sys
import psycopg2 as sql

import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

sys.path.append(os.path.abspath('/srv/lib/'))
from util import get_words


class Model:
	X = []
	Y = []
	offsets = defaultdict(int)

	def __init__(self, db_tweets_cursor, training):
		print("Attempting to load model from", self.path)
		if os.path.isfile(self.path):
			return self.load()

		print("No model found at", self.path)
		print("Loading tweets to train new model")
		for t in training:
			t['cached'] = len(Model.offsets[t['string']])
			t['remain'] = t['limit'] - t['cached']

			print("Label:", t['string'])
			print("Loading", t['limit'], "tweets from db and cache. Cached:", t['cached'])

			if t['remain'] <= 0:
				continue

			db_tweets_cursor.execute("""
					SELECT text
					FROM tweets
					INNER JOIN tweet_metadata ON
						id=tweet_id AND
						final=TRUE AND
						""" +t['string']+ """
					LIMIT %s
					OFFSET %s
					ORDER BY id ASC
				""", (t['remain'], t['cached']))

			tweets = db_tweets_cursor.fetchall()
			for text, in tweets:
				if not get_words(text):
					print("WARNING: Empty tweet loaded:", text)

				Model.X.append(text)
				Model.Y.append(t['string'])

			Model.offsets[t['string']] += len(tweets)
			print("Loaded", len(tweets), "new tweets tagged as:", t['string'])
		print("Database load finished. Total:", len(Model.X), "tweets")

		print("Training new model", self.path)
		model = self.train(self.preprocess_x(Model.X)[:self.training_size], self.preprocess_y(Model.Y)[:self.training_size])

		print("Saving new model", self.path)
		self.save()
		return model


class Tweet2Vec(Model):
	path='/srv/tweet2vec.model'

	def load(self):
		self.model = Doc2Vec.load(self.path)

	def preprocess_x(self, X):
		return [TaggedDocument(get_words(tweet), [category]) for tweet, category in zip(X, Model.Y[:len(X)])]

	def preprocess_y(self, Y):
		return Y

	def train(self, X, Y):
		self.model = Doc2Vec(
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
			)

	def save(self):
		self.model.save(self.path)

	def get_vector(self, tweet):
		return self.model.infer_vector(get_words(tweet), alpha=0.1, min_alpha=0.0001, steps=5)


class RandomForest(Model):
	path='/srv/random_forest.model'

	def load(self):
		self.model = random_forest.TensorForestEstimator(
				tensor_forest.ForestHParams(
						num_classes=2,
						num_features=784,
						num_trees=100,
						max_nodes=1000
					),
				graph_builder_class=tensor_forest.RandomForestGraphs if True else tensor_forest.TrainingLossForest,
				model_dir=self.path
			)

	def preprocess_x(self, X):
		return numpy.array([RandomForest.t2v.get_vector(tweet).tolist() for tweet in X]).astype(numpy.float32)

	def preprocess_y(self, Y):
		return numpy.array(Y).astype(numpy.float32)

	def train(self, X, Y):
		self.load()
		self.model.fit(
				input_fn=numpy_io.numpy_input_fn(
						x={'features': X},
						y=Y,
						batch_size=1000,
						num_epochs=None,
						shuffle=True
					),
				steps=None
			)

	def save(self):
		pass

	def predict(self, X):
		self.model.predict(
				input_fn=numpy_io.numpy_input_fn(
						x={'features': X},
						batch_size=1000,
						num_epochs=1,
						shuffle=False
					)
			)
