from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config, db_tweets_connect

import numpy

class Model:
	Xs = {}
	Ys = {}

	def __init__(self, dataset, properties='exact', input_fn=None, load=True):
		self.name = self.__class__.__name__.lower()
		self.dataset = dataset
		self.input_fn = input_fn if input_fn else lambda X, Y: (X, Y)
		self.properties = properties

		if not isinstance(self.properties, list):
			self.properties = [self.properties]

		if load:
			self.load()

	def load(self):
		if self.dataset is not None:
			self.path = '/srv/models/' + self.name + '_' + self.dataset
			try:
				print("Loading model", self.name, "for dataset", self.dataset)
				self.cache()
				print("Succesfully loaded cached model:", self.path)
			except Exception, e:
				print("Unable to load from cache:", e)

				print("Creating new model:", self.path)
				X, Y = self.training_data()

				print("Training model")
				X, Y = self.input_fn(X, Y)
				self.train(X, Y)
				print("Loading model off disk")
				self.cache()
				print("New model created", self.path)
		else:
			print("Loading meta model:", self.name)
			self.cache()

	def training_data(self):
		if self.dataset in Model.Xs:
			print("Using cached dataset:", self.dataset)
			return (Model.Xs[self.dataset], Model.Ys[self.dataset])

		Model.Xs[self.dataset] = []
		Model.Ys[self.dataset] = []

		db_tweets_connection = db_tweets_connect('pericog', config('connections', config('connections', 'active')))
		db_tweets_cursor = db_tweets_connection.cursor()

		print("Retrieving training dataset:", self.dataset)
		db_tweets_cursor.execute("""
				SELECT
					text, {}
				FROM tweets
				LEFT JOIN tweet_properties ON
					id=tweet_id
				WHERE {}_train = True
			""".format(
				','.join(self.properties),
				self.dataset
			))

		# TODO: make this work with multiple properties at once
		for text, label in db_tweets_cursor.fetchall():
			if label is None:
				continue

			Model.Xs[self.dataset].append(text)
			Model.Ys[self.dataset].append(label)

		db_tweets_connection.close()

		return (
				Model.Xs[self.dataset],
				numpy.array(Model.Ys[self.dataset]).astype(numpy.bool)
			)
