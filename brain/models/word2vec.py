from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

import gensim
import numpy

def get_word2vec(token, vectors, size=300):
	if token in vectors:
		return vectors[token]
	elif config('word2vec', 'generate_missing'):
		return numpy.random.rand(size)
	else:
		return numpy.zeros(size)

class word2vec(Model):
	def load(self, vectors):
		self.vectors = vectors

	def train(self, X, Y):
		pass

	def predict(self, X):
		X, Y = self.input_function(X, [])
		return [[get_word2vec(token, self.vectors) for token in tokens_list] for tokens in X]
