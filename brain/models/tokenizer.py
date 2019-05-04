# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

import re
from unidecode import unidecode

class tokenizer(Model):
	def load(self):
		pass

	def train(self, X, Y):
		pass

	def predict(self, X):
		# adapted from Romain Paulus and Jeffrey Pennington's Ruby tweet tokenizer

		def sub(pattern, output, string, whole_word=False):
			token = output
			if whole_word:
				pattern = r'(?:\s|^)' + pattern + r'(?:\s|$)'

			if isinstance(output, basestring):
				token = ' ' + output + ' '
			else:
				token = lambda match: ' ' + output(match) + ' '

			return re.sub(pattern, token, string)

		def hashtag(token):
			token = token.group('tag')
			if token != token.upper():
				token = ' '.join(re.findall('[a-zA-Z][^A-Z]*', token))

			return '<hashtag> ' + token + ' <endhashtag>'

		def punc_repeat(token):
			return token.group(0)[0] + ' <repeat>'

		def punc_separate(token):
			return token.group()

		def number(token):
			return token.group() + ' <number>';

		def word_end_repeat(token):
			return token.group(1) + token.group(2) + ' <elong>'

		eyes        = r"[8:=;]"
		nose        = r"['`\-\^]?"
		sad_front   = r"[(\[/\\]+"
		sad_back    = r"[)\]/\\]+"
		smile_front = r"[)\]]+"
		smile_back  = r"[(\[]+"
		lol_front   = r"[DbpP]+"
		lol_back    = r"[d]+"
		neutral     = r"[|]+"
		sadface     = eyes + nose + sad_front   + '|' + sad_back   + nose + eyes
		smile       = eyes + nose + smile_front + '|' + smile_back + nose + eyes
		lolface     = eyes + nose + lol_front   + '|' + lol_back   + nose + eyes
		neutralface = eyes + nose + neutral     + '|' + neutral    + nose + eyes
		punctuation = r"""[ '!"#$%&'()+,/:;=?@_`{|}~\*\-\.\^\\\[\]]+""" # < and > omitted to avoid messing up tokens

		tokens = []
		for tweet in X:
			tweet = sub(r'[\s]+',                             '  ',            tweet) # ensure 2 spaces between everything
			tweet = sub(r'(?:(?:https?|ftp)://|www\.)[^\s]+', '<url>',         tweet, True)
			tweet = sub(r'@\w+',                              '<user>',        tweet, True)
			tweet = sub(r'#(?P<tag>\w+)',                     hashtag,         tweet, True)
			tweet = sub(sadface,                              '<sadface>',     tweet, True)
			tweet = sub(smile,                                '<smile>',       tweet, True)
			tweet = sub(lolface,                              '<lolface>',     tweet, True)
			tweet = sub(neutralface,                          '<neutralface>', tweet, True)
			tweet = sub(r'(?:<3+)+',                          '<heart>',       tweet, True)
			tweet = tweet.lower()
			tweet = sub(r'[-+]?[.\d]*[\d]+[:,.\d]*',          number,          tweet, True)
			tweet = sub(punctuation,                          punc_separate,   tweet)
			tweet = sub(r'([!?.])\1+',                        punc_repeat,     tweet)
			tweet = sub(r'(\S*?)(\w)\2+\b',                   word_end_repeat, tweet)

			tweet = unicode(unidecode(tweet))
			tweet = tweet.split()
			tokens.append(tweet)
		return tokens
