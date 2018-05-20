from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

import gensim
import numpy

def get_word2vec(token, vector, size=300):
	if token in vector:
		return vector[token]
	elif config('word2vec', 'generate_missing'):
		return numpy.random.rand(size)
	else:
		return numpy.zeros(size)

def get_average_word2vec(tokens_list, vector):
	vectorized = [get_word2vec(token, vector) for token in tokens_list]
	return numpy.divide(
			numpy.sum(vectorized, axis=0),
			len(vectorized)
		)

class word2vec(Model):
	def load(self):
		self.vectors = gensim.models.KeyedVectors.load_word2vec_format(self.path, binary=True)

	def train(self, X, Y):
		pass

	def predict(self, X):
		X, Y = self.input_function(X, [])
		return [get_average_word2vec(tokens, self.vectors) for tokens in X]
