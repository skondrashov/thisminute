from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import get_words, config
import Model

from gensim.models import Doc2Vec as GS_Doc2Vec
from gensim.models.doc2vec import TaggedDocument

class Doc2Vec(Model):
	def load(self, path):
		try:
			self.d2v = GS_Doc2Vec.load(path)
			return
		except:
			if not train:
				return

		self.training_data()
		self.d2v = Doc2Vec(
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

				documents=Model.Xs[self.dataset],
			)
		self.d2v.save(path)

	def predict(self, X):

		numpy.array(X).astype(numpy.float32)
		return self.d2v.infer_vector(get_words(tweet), alpha=0.1, min_alpha=0.0001, steps=5).tolist()
