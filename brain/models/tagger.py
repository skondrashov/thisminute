from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config, db_tweets_connect
import Model

class tagger(Model):
	def load(file):
		self.db_tweets_connection = db_tweets_connect('pericog', config('connections', config('connections', 'active')))
		self.db_tweets_cursor = db_tweets_connection.cursor()

	def train(self):
		self.db_pericog.execute("""
				INSERT INTO tweet_labels
					tweet_id,
					text,
					model_id
				VALUES
					%s,
					%s,
					'tagger_crowdflower'
			""", (tweet_id, text))

	def predict(self, X):
		pass
