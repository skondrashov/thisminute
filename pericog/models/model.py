from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config, db_tweets_connect

import numpy

# for use by the factory method
sys.path.append(os.path.abspath('/srv/lib/models'))

class Model:
	Xs = {}
	Ys = {}

	def __init__(self, dataset=None, properties='True', input_model=None, verbose=False):
		self.name = self.__class__.__name__.lower()
		self.dataset = dataset
		self.properties = properties
		self.input_function = lambda X, Y: (input_model.predict(X) if input_model else X, Y)
		self.verbose = verbose

		if not isinstance(self.properties, list):
			self.properties = [self.properties]

	def factory(self, model, dataset=None, properties='True', input_model=None):
		model = config(self.name, model)
		Class = getattr(__import__(model, fromlist=[model]), model)
		return Class(dataset, properties, input_model, self.verbose)

	def load_and_train(self):
		if self.dataset is None:
			print("Loading unsupervised model", self.name)
		else:
			self.path = '/srv/models/' + self.name + '_' + self.dataset
			print("Loading model", self.name, "using training set", self.dataset)
			try:
				self.load()
				print("Successfully loaded cached model:", self.path)
				return
			except Exception, e:
				print("Unable to load from cache:", e)

			print("Creating new model:", self.path)
			X, Y = self.training_data()

			print("Training model")
			X, Y = self.input_function(X, Y)
			self.train(X, Y)
			print("New model created", self.path)

		self.load()

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
