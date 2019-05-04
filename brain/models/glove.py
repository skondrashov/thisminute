from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

import numpy

class glove(Model):
	def load(self):
		with open(self.path, 'r') as file:
			self.vectors = {}
			for line in file:
				values = line.rstrip().split(' ')
				self.vectors[values[0]] = numpy.asarray(values[1:])
		self.size = len(values[1:])

	def train(self, X, Y):
		pass

	def predict(self, X):
		X, Y = self.input_function(X, [])

		def get_word2vec(token):
			if token in self.vectors:
				return self.vectors[token]
			elif config('glove', 'generate_missing'):
				return numpy.random.rand(self.size)
			else:
				return numpy.zeros(self.size)

		return [[get_word2vec(token) for token in tokens] for tokens in X]
