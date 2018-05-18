from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

from sklearn.externals import joblib
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

class Bag_Of_Words_Count(Model):
	def cache(self):
		self.bag_of_words_count = joblib.load(self.path)

	def train(self, X, Y):
		bag_of_words_count = TfidfVectorizer()# CountVectorizer()
		bag_of_words_count.fit(X)
		joblib.dump(bag_of_words_count, self.path)

	def predict(self, X):
		return self.bag_of_words_count.transform(X)
