from __future__ import print_function
from __future__ import division

import numpy

from gensim.models import Doc2Vec
from gensim.models.doc2vec import TaggedDocument

from tensorflow.contrib.tensor_forest.client import random_forest
from tensorflow.contrib.tensor_forest.python import tensor_forest
from tensorflow.python.estimator.inputs import numpy_io

import os
import sys
import mysql.connector

import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

sys.path.append(os.path.abspath('/srv/lib/'))
from util import get_words

class Model:
	X = []
	Y = []
	offsets = {True: 0, False: 0, 'extra': 0}

	def __init__(self, db_name, training_size):
		self.training_size = training_size

		print("Connecting to", db_name)
		db_tweets_connection = mysql.connector.connect(
				user='pericog',
				password=open('/srv/auth/mysql/pericog.pw').read(),
				host=config.get('connections', db_name),
				database='ThisMinute'
			)
		self.db_tweets_cursor = db_tweets_connection.cursor()

		print("Attempting to load model from ", self.path)
		if os.path.isfile(self.path):
			return self.load()

		remain = lambda: training_size - len(Model.X)

		print("No model found at", self.path)
		print("Loading", training_size, "tweets to train new model")
		print(len(Model.X), "tweets in cache, loading", remain(), "more")

		for category in [True, False]:
			if remain() <= 0:
				break
			self.db_tweets_cursor.execute("""
					SELECT text
					FROM tagged_tweets
					WHERE master_sentiment=%s
					LIMIT %s, %s
				""", (category, remain(), Model.offsets[category]))

			count = self.load_tweets(category)
			print("Loaded", count, "tweets tagged as:", category)
			Model.offsets[category] += count

		if remain() > 0:
			self.db_tweets_cursor.execute("""
					SELECT text
					FROM training_tweets
					LIMIT %s, %s
				""", (remain(), Model.offsets['extra']))

			count = self.load_tweets(category)
			print("Loaded", count, "untagged tweets; assumed label:", category)
			Model.offsets['extra'] += count

		print("Loading finished. Total:", len(Model.X), "tweets")
		print("Training new model", self.path)
		model = self.train(self.preprocess_x(Model.X)[:self.training_size], self.preprocess_y(Model.Y)[:self.training_size])

		print("Saving new model", self.path)
		self.save()
		return model

	def load_tweets(self, label):
		tweets = self.db_tweets_cursor.fetchall()
		for text, in tweets:
			count = len(Model.X)
			if count >= self.training_size:
				return
			if not get_words(text):
				continue

			if not count % 10000:
				print("Loaded", count, "tweets. Sample:", text)

			Model.X.append(text)
			Model.Y.append(label)
		return len(tweets)


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
