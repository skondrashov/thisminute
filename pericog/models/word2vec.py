from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

import gensim
import numpy

def get_average_word2vec(tokens_list, vector, generate_missing=False, k=300):
	if len(tokens_list)<1:
		return numpy.zeros(k)
	if generate_missing:
		vectorized = [vector[word] if word in vector else numpy.random.rand(k) for word in tokens_list]
	else:
		vectorized = [vector[word] if word in vector else numpy.zeros(k) for word in tokens_list]
	length = len(vectorized)
	summed = numpy.sum(vectorized, axis=0)
	return numpy.divide(summed, length)

class Average_Word2Vec(Model):
	def cache(self):
		self.vectors = gensim.models.KeyedVectors.load_word2vec_format(self.path, binary=True)

	def train(self, X, Y):
		pass

	def predict(self, X):
		X, Y = self.input_fn(X, [])
		return [get_average_word2vec(tokens, self.vectors) for tokens in X]
