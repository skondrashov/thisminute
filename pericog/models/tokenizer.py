from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

import re
from unidecode import unidecode

class Tokenizer(Model):
	def cache(self):
		pass

	def train(self, X, Y):
		pass

	def predict(self, X):
		tokens = []
		for tweet in X:
			tweet = re.sub('((\B@)|(\\bhttps?:\/\/))[^\\s]+', " ", tweet)
			tweet = re.sub('[^\w]+', " ", tweet)
			tweet = tweet.lower().strip()
			tweet = unicode(unidecode(tweet))
			tokens.append(tweet.split())
		return tokens
