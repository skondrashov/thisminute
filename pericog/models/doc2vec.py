from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

import numpy

from util import get_words, config
from model import Model

from gensim.models import Doc2Vec as GS_Doc2Vec
from gensim.models.doc2vec import TaggedDocument

class Doc2Vec(Model):
	def load(self):
		try:
			self.d2v = GS_Doc2Vec.load(self.path)
			print("Using existing model:", self.path)
			self.trained=True
			return
		except:
			self.trained=False

	def train(self, X, Y):
		print("Training new model:", self.name)
		X = [TaggedDocument(get_words(tweet), [property]) for tweet, property in zip(X, Y)]
		self.d2v = GS_Doc2Vec(
				dm=1, dbow_words=1, dm_mean=0, dm_concat=0, dm_tag_count=1,
				hs=1,
				negative=0,

				size=int(config('tweet2vec', 'vector_size')),
				alpha=0.025,
				window=8,
				min_count=0,
				sample=1e-4,
				iter=10,

				max_vocab_size=None,
				workers=int(config('tweet2vec', 'thread_count')),
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
		self.d2v.save(self.path)

	def predict(self, tweet):
		return self.d2v.infer_vector(get_words(tweet), alpha=0.1, min_alpha=0.0001, steps=5)
