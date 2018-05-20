from __future__ import print_function
from __future__ import division
import sys, os

sys.path.append(os.path.abspath('/srv/lib/'))
from util import config, db_tweets_connect
from model import Model

import numpy
import pandas
from nltk.tokenize import RegexpTokenizer
from sklearn.decomposition import PCA, TruncatedSVD
import matplotlib
import matplotlib.pyplot as pyplot
import matplotlib.patches as mpatches

class pericog(Model):
	def load(self):
		tokenizer = self.factory(
				'tokenizer'
			)
		tokenizer.load_and_train()

		tokens2vec = self.factory(
				'tokens2vec',
				dataset='google_news',
				input_function=lambda X, Y: (tokenizer.predict(X), Y)
			)
		tokens2vec.load_and_train()

		classifier = self.factory(
				'classifier',
				dataset='random_forest',
				properties='crowdflower',
				input_function=lambda X, Y: (tokens2vec.predict(X), Y)
			)

		if self.verbose:
			X, Y = classifier.training_data()
			self.analyze(X, Y, lambda X, Y: (tokens2vec.predict(X), Y))

		classifier.load_and_train()
		self.model = classifier

	def predict(self, X):
		return self.model.predict(X)

	def analyze(self, X, Y, input_fn):
		tokenizer = RegexpTokenizer(r'\w+')
		dataset = pandas.DataFrame({'text': X, 'label': Y})
		dataset.head()
		print(dataset.groupby('label').count())

		tokens = dataset['text'].apply(tokenizer.tokenize)
		tokens.head()

		all_words = [word for tweet in tokens for word in tweet]
		sentence_lengths = [len(tweet) for tweet in tokens]
		VOCAB = sorted(list(set(all_words)))
		print("\n%s words total, with a vocabulary size of %s" % (len(all_words), len(VOCAB)))
		print("Max sentence length is %s" % max(sentence_lengths))

		figure = pyplot.figure(figsize=(10, 10))
		pyplot.xlabel('Sentence length')
		pyplot.ylabel('Number of sentences')
		pyplot.hist(sentence_lengths)
		pyplot.show()

		X, Y = input_fn(X, Y)

 		def plot_LSA(test_data, test_labels, savepath="PCA_demo.csv", plot=True):
			lsa = TruncatedSVD(n_components=2)
			lsa.fit(test_data)
			lsa_scores = lsa.transform(test_data)
			if plot:
				pyplot.scatter(lsa_scores[:,0], lsa_scores[:,1], s=8, alpha=.8, c=test_labels, cmap=matplotlib.colors.ListedColormap(['orange', 'blue']))
				orange_patch = mpatches.Patch(color='orange', label='Irrelevant')
				blue_patch = mpatches.Patch(color='blue', label='Disaster')
				pyplot.legend(handles=[orange_patch, blue_patch], prop={'size': 30})

		figure = pyplot.figure(figsize=(16, 16))
		plot_LSA(X, Y)
		pyplot.show()
