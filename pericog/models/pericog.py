from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config, db_tweets_connect
from model import Model
from tokenizer import Tokenizer
from doc2vec import Doc2Vec
from random_forest import Random_Forest
from bag_of_words_count import Bag_Of_Words_Count
from word2vec import Average_Word2Vec

import numpy
import pandas
from nltk.tokenize import RegexpTokenizer
from sklearn.decomposition import PCA, TruncatedSVD
import matplotlib
import matplotlib.pyplot as pyplot
import matplotlib.patches as mpatches

class Pericog(Model):
	def cache(self):
		self.tokenizer =\
			Tokenizer(None)

		def tweet2vec_input(X, Y):
			return self.tokenizer.predict(X), Y
		self.tweet2vec =\
			Average_Word2Vec('google_news', input_fn=tweet2vec_input)
			# Doc2Vec('tweet2vec', input_fn=tweet2vec_input)
			# Bag_Of_Words_Count('tweet2vec', input_fn=tweet2vec_input)

		def classifier_input(X, Y):
			return self.tweet2vec.predict(X), Y
		self.classifier =\
			Random_Forest('random_forest', properties='crowdflower', input_fn=classifier_input, load=False)

		X, Y = self.classifier.training_data()
		self.analyze(X, Y, classifier_input)

		self.classifier.load()

	def predict(self, X):
		return self.classifier.predict(X)

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

		fig = pyplot.figure(figsize=(10, 10))
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

		fig = pyplot.figure(figsize=(16, 16))
		plot_LSA(X, Y)
		pyplot.show()
