from __future__ import print_function
from __future__ import division
import sys, os

sys.path.append(os.path.abspath('/srv/lib/'))
from util import config, db_tweets_connect
from model import Model

import logging, time

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

# from tagger import tagger
# tagger = tagger('tagger', dataset='tagger')

print("Connecting to self")
db_pericog_connection = db_tweets_connect('pericog', 'localhost')
db_pericog_cursor = db_pericog_connection.cursor()

print("Connecting to tweets")
ACTIVE_DB_NAME = config('connections', 'active')
db_tweets_connection = db_tweets_connect('pericog', config('connections', ACTIVE_DB_NAME))
db_tweets_cursor = db_tweets_connection.cursor()

while True:
	print("Executing query...")
	db_tweets_cursor.execute("""
			UPDATE tweet_properties SET
				tagger_train = True
			WHERE tweet_id IN (
					SELECT tweet_id
					FROM tweet_properties
					WHERE tagger_train = True
					LIMIT 100
				)
			RETURNING tweet_id
		""")
	tweet_ids = [str(tweet_id) for tweet_id, in db_tweets_cursor.fetchall()]

	db_tweets_cursor.execute("""
				SELECT
					text
				FROM tweets
				WHERE id IN ({})
			""".format(
				','.join(tweet_ids)
			)
		)
	tweet_texts = [tweet_text for tweet_text, in db_tweets_cursor.fetchall()]

	placeholders = '),('.join([tweet_id + ",'tagger',%s" for tweet_id in tweet_ids])

	db_pericog_cursor.execute("""
				INSERT INTO tweet_labels
					(tweet_id, model_id, text)
				VALUES
					({})
			""".format(
				placeholders
			),
			tweet_texts
		)

	db_pericog_connection.commit()
	# ids = []
	# X = []
	# for id, timestamp, geolocation, exact, user, text in tweets:

	# 	ids.append(id)
	# 	X.append(text)

	# db_tweets_connection.commit()

	# if X:
	# 	Y = pericog.predict(X)

	# 	for id, tweet, label in zip(ids, X, Y):
	# 		if label == True:
	# 			db_pericog_cursor.execute("""
	# 					INSERT INTO whitelist
	# 						(tweet_id, tagger_train)
	# 					VALUES
	# 						(%s, True)
	# 					ON CONFLICT DO UPDATE
	# 				""", (id))

		# print("Positives:")
		# for row in zip(X,Y):
		# 	if row[1]:
		# 		print(row[0])

		# print("Negatives:")
		# for row in zip(X,Y):
		# 	if not row[1]:
				# print(row[0])

	# time.sleep(1)





# class tagger(Model):
# 	def load(self):
# 		pass

# 	def train(self):
# 		pass

# 	def predict(self, X):
# 		for tweet in X:
# 			yield input(tweet, )
