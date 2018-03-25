from __future__ import print_function
from __future__ import division

from util import db_tweets_connect, config

class Model:
	Xs = {}

	def __init__(self):
		self.name = type(self).__name__.lower()
		self.dataset = config('datasets', self.name)
		self.load('/srv/models/' + self.name + '_' + self.dataset)

	def training_data(self, dataset):
		if Model.Xs[self.dataset]:
			return

		Model.Xs[self.dataset] = []

		db_tweets_connection = db_tweets_connect('pericog', config('connections', ACTIVE_DB_NAME))
		db_tweets_cursor = db_tweets_connection.cursor()

		db_tweets_cursor.execute("""
			SELECT
				text, {}
			FROM tweet_properties
			JOIN tweets ON
				id=tweet_id
			WHERE {}_train = True
		""".format(self.dataset, self.name))
		for text, label in db_tweets_cursor.fetchall():
			if not get_words(text):
				continue

			Model.Xs[self.dataset].append(text)
			Model.Ys[self.dataset].append(label)

		db_tweets_connection.close()
