from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import db_tweets_connect, config

class Model:
	Xs = {}
	Ys = {}

	def __init__(self, dataset, properties='exact', input_fn=None):
		self.name = self.__class__.__name__.lower()
		self.dataset = dataset
		self.input_fn = input_fn if input_fn else lambda X, Y: (X, Y)
		self.properties = properties

		if not isinstance(self.properties, list):
			self.properties = [self.properties]

		if dataset is not None:
			self.path = '/srv/models/' + self.name + '_' + self.dataset
			try:
				print("Loading model", self.name, "for dataset", self.dataset)
				self.load()
				print("Succesfully loaded cached model:", self.path)
			except:
				print("Creating new model:", self.path)
				X, Y = self.training_data()
				X, Y = self.input_fn(X, Y)
				print("Training model")
				self.train(X, Y)
				print("Loading model off disk")
				self.load()
				print("New model created", self.path)
		else:
			print("Loading meta model:", self.name)
			self.load()

	def training_data(self):
		if self.dataset in Model.Xs:
			print("Using cached dataset:", self.dataset)
			return (Model.Xs[self.dataset], Model.Ys[self.dataset])

		Model.Xs[self.dataset] = []
		Model.Ys[self.dataset] = []

		db_tweets_connection = db_tweets_connect('pericog', config('connections', config('connections', 'active')))
		db_tweets_cursor = db_tweets_connection.cursor()

		print("Retrieving training set:", self.dataset)
		db_tweets_cursor.execute("""
				SELECT
					text, {}
				FROM tweet_properties
				JOIN tweets ON
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

		return (Model.Xs[self.dataset], Model.Ys[self.dataset])
