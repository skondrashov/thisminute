from __future__ import print_function
from __future__ import division
import sys, os

sys.path.append(os.path.abspath('/srv/lib/'))
from util import config, db_tweets_connect
from model import Model

import pandas
from nltk.tokenize import RegexpTokenizer
from sklearn.decomposition import PCA, TruncatedSVD
import matplotlib
import matplotlib.pyplot as pyplot
import matplotlib.patches as mpatches

class tokens2sentiment(Model):
	def load(self):
		vectors = gensim.models.KeyedVectors.load_word2vec_format(self.path, binary=True)

		token_vectorizer = self.factory(
				'token_vectorizer',
				input_model=tokenizer,
			)
		token_vectorizer.load(vectors)

		document_vectorizer = self.factory(
				'document_vectorizer',
				input_model=token_vectorizer,
			)
		document_vectorizer.load(vectors)

		self.model = classifier

	def predict(self, X):
		return self.model.predict(X)
