from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

from torchtext import data
from torchtext import datasets

from cove import MTLSTM

inputs = data.Field(lower=True, include_lengths=True, batch_first=True)
answers = data.Field(sequential=False)

print('Generating train, dev, test splits')
train, dev, test = datasets.SNLI.splits(inputs, answers)

print('Building vocabulary')
inputs.build_vocab(train, dev, test)
inputs.vocab.load_vectors(vectors=GloVe(name='840B', dim=300))
answers.build_vocab(train)

train_iter, dev_iter, test_iter = data.BucketIterator.splits(
		(train, dev, test),
		batch_size=100,
		device=0
	)

train_iter.init_epoch()
print('Generating CoVe')
for batch_idx, batch in enumerate(train_iter):
	self.model.train()
	cove_premise = model(*batch.premise)
	cove_hypothesis = model(*batch.hypothesis)

import gensim
import numpy

def get_cove(token_vectors, vector, size=300):
	if token in vectors:
		return vectors[token]
	elif config('word2vec', 'generate_missing'):
		return numpy.random.rand(size)
	else:
		return numpy.zeros(size)

class tmcove(Model):
	def load(self, vectors):
		self.model = MTLSTM(n_vocab=len(vectors.keys()), vectors=vectors)
		self.model.cuda()

	def train(self, X, Y):
		pass

	def predict(self, X):
		X, Y = self.input_function(X, [])
		return [[get_word2vec(token, self.vectors) for token in tokens_list] for tokens in X]
