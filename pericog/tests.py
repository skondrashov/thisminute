#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division

import shutil
import os
import sys
import tensorflow

import unittest

sys.path.append(os.path.abspath('/srv/lib/'))
tensorflow.logging.set_verbosity(tensorflow.logging.ERROR)

TEST_DB_ADDRESS = 'tweets-dev.thisminute.org'

tweets = [
		u"""The #QueensCourt was too lit last night @TsMadisonatl1 & @QueenKhia “FUCK YOU!!!You 17 pack Hot Dog neck having ass bitch” 😂😂😂😂 pic.twitter.com/nOdgu8wyCy"""
	]
labels = [
		False
	]
words = [
		[u'the', u'queenscourt', u'was', u'too', u'lit', u'last', u'night', u'fuck', u'you', u'you', u'17', u'pack', u'hot', u'dog', u'neck', u'having', u'ass', u'bitch', u'pic', u'twitter', u'com', u'nodgu8wycy']
	]

db_tweets_connection = util.db_tweets_connect('pericog', TEST_DB_ADDRESS, True)
db_tweets_cursor = db_tweets_connection.cursor()

import util

class GetWordsTest(unittest.TestCase):
	def test_mentions(self):
		self.assertEqual(util.get_words(tweets[0]), words[0])


import models

models.Model.X = tweets
models.Model.Y = labels
models.Tweet2Vec.path = '/srv/tweet2vec_test.model'
models.RandomForest.path = '/srv/random_forest_test.model'

class Tweet2VecTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.model = models.Tweet2Vec(db_tweets_cursor, {
				{
					'string':'legible=TRUE',
					'limit': 10
				}
			})

	def test_load(self):
		self.model.load()

	def test_preprocess_x(self):
		self.model.preprocess_x(tweets)

	def test_preprocess_y(self):
		self.model.preprocess_y(labels)

	def test_train(self):
		self.model.train(self.model.preprocess_x(tweets), self.model.preprocess_y(labels))

	def test_get_vector(self):
		self.model.get_vector(tweets[0])

	@classmethod
	def tearDownClass(cls):
		os.remove(models.Tweet2Vec.path)

class RandomForestTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		models.RandomForest.t2v = models.Tweet2Vec(db_tweets_cursor, {
				{
					'string':'legible=TRUE',
					'limit': 10
				}
			})
		cls.model = models.RandomForest(db_tweets_cursor, {
				{
					'string':'informative=TRUE',
					'limit': 10
				},
				{
					'string':'informative=FALSE',
					'limit': 10
				}
			})

	def test_load(self):
		self.model.load()

	def test_preprocess_x(self):
		self.model.preprocess_x(tweets)

	def test_preprocess_y(self):
		self.model.preprocess_y(labels)

	def test_train(self):
		self.model.train(self.model.preprocess_x(tweets), self.model.preprocess_y(labels))

	def test_predict(self):
		self.model.predict(self.model.preprocess_x(tweets))

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(models.RandomForest.path)
