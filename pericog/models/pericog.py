from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

import numpy

from util import db_tweets_connect, config
from model import Model
from doc2vec import Doc2Vec
from random_forest import Random_Forest

class Pericog(Model):
	def load(self):
		dataset='tweet2vec'
		print("Loading tweet2vec model for dataset:", dataset)
		self.t2v = Doc2Vec(dataset)
		if not self.t2v.trained:
			X, Y = self.t2v.training_data()
			self.t2v.train(X, Y)

		dataset = 'random_forest'
		print("Loading random forest model for dataset:", dataset)
		self.rf = Random_Forest(dataset)
		if not self.rf.trained:
			print("Retrieving training set:", dataset)
			X, Y = self.rf.training_data()
			X = [self.t2v.predict(tweet).tolist() for tweet in X]
			X = numpy.array(X).astype(numpy.float32)
			Y = numpy.array(Y).astype(numpy.float32)
			self.rf.train(X, Y)

	def predict(self, X):
		X = [self.t2v.predict(tweet).tolist() for tweet in X]
		X = numpy.array(X).astype(numpy.float32)
		X = self.rf.predict(X)

		return X
