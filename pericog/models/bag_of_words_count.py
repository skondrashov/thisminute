from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

from sklearn.externals import joblib
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

class bag_of_words_count(Model):
	def load(self):
		self.model = joblib.load(self.path)

	def train(self, X, Y):
		model = TfidfVectorizer()# CountVectorizer()
		model.fit(X)
		joblib.dump(model, self.path)

	def predict(self, X):
		return self.model.transform(X)
