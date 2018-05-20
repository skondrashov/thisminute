from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config, get_words
from model import Model

from gensim.models import Doc2Vec
from gensim.models.doc2vec import TaggedDocument

class doc2vec(Model):
	def load(self):
		self.model = Doc2Vec.load(self.path)

	def train(self, X, Y):
		X = [TaggedDocument(tokens, [property]) for tokens, property in zip(X, Y)]
		model = Doc2Vec(
				workers=config('pericog', 'thread_count'),

				dm=1, dbow_words=1, dm_mean=0, dm_concat=0, dm_tag_count=1,
				hs=1,
				negative=0,

				size=config('tokens2vec', 'vector_size'),
				alpha=0.025,
				window=8,
				min_count=0,
				sample=1e-4,
				iter=10,

				max_vocab_size=None,
				batch_words=1000000,
				min_alpha=0.0001,
				seed=1,

				### no documentation ###
				# docvecs=None,
				# docvecs_mapfile='',
				# trim_rule=None,
				# comment=None,

				documents=X,
			)
		model.save(self.path)

	def predict(self, X):
		return [self.model.infer_vector(tokens, alpha=0.1, min_alpha=0.0001, steps=5) for tokens in X]
