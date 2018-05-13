from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

import numpy as np

from util import db_tweets_connect, config
from model import Model
from doc2vec import Doc2Vec
from random_forest import Random_Forest

class Pericog(Model):
	def load(self):
		self.t2v = Doc2Vec('tweet2vec')

		def rf_input(X, Y):
			X = [self.t2v.predict(tweet).tolist() for tweet in X]
			X = np.array(X).astype(np.float32)
			Y = np.array(Y).astype(np.bool)
			return X, Y

		self.rf = Random_Forest('random_forest', properties='crowdflower', input_fn=rf_input)

	def predict(self, X):
		return self.rf.predict(X)
