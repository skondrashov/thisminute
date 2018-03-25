from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

import Model

class Tagger(Model):
	def __init__(self, db_pericog, db_tweets, file):
		pass

	def load(file):
		pass

	def train(self):
		pass

	def read_data(self):
		self.db_tweets.execute("""
				SELECT
					tweet_id,
					text
				FROM tweet_properties
				JOIN tweets ON id=tweet_id
				WHERE
					crowdflower IS NOT NULL AND
					secondhand IS NULL AND
					eyewitness IS NULL
			""")

		for tweet_id, text in db_tweets_cursor.fetchall():
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

	def run():
		pass
