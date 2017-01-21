#!/usr/bin/python
import logging, time
from daemon import runner

import ConfigParser
import mysql.connector

from gensim.models import Doc2Vec
from gensim.models.doc2vec import TaggedDocument

import re
from unidecode import unidecode

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

TARGET_IP   = config.get('connections', config.get('connections', 'active'))
VECTOR_SIZE = int(config.get('tweet2vec', 'vector_size'))
THREAD_COUNT = int(config.get('optimization', 'thread_count'))

db_connection = mysql.connector.connect(
		user='tweet2vec',
		password=open('/srv/auth/daemons/tweet2vec.pw').read(),
		host=TARGET_IP,
		database='ThisMinute'
	)
db_cursor = db_connection.cursor()

def get_words(tweet):
	tweet = re.sub('((\B@)|(\\bhttps?:\/\/))[^\\s]+', " ", tweet)
	tweet = re.sub('[^\w]+', " ", tweet)
	tweet = tweet.lower().strip()
	tweet = unicode(unidecode(tweet))
	return tweet.split()

print "Loading tweets"
db_cursor.execute('SELECT tweet_id, text FROM training_tweets')

# prolly multithread this: build chunks in workers then concat them together into one list
tweets = []
for tweet_id, text in db_cursor.fetchall():
	words = get_words(text)
	if words:
		tweets.append(TaggedDocument(words, [tweet_id]))

print "Training model"
d2v = Doc2Vec(
		dm=1, dbow_words=1, dm_mean=0, dm_concat=0, dm_tag_count=1,
		hs=1,
		negative=0,

		size=VECTOR_SIZE,
		alpha=0.025,
		window=8,
		min_count=0,
		sample=1e-4,
		iter=10,

		max_vocab_size=None,
		workers=THREAD_COUNT,
		batch_words=1000000,
		min_alpha=0.0001,
		seed=1,

		### no documentation ###
		# docvecs=None,
		# docvecs_mapfile='',
		# trim_rule=None,
		# comment=None,

		documents=tweets,
	)
print "Training complete"

while True:
	db_cursor.execute('DELETE FROM tweet_vectors WHERE status = 2')

	db_cursor.execute("""
		SELECT tweets.id, tweets.text
		FROM tweet_vectors
		JOIN tweets ON tweets.id = tweet_vectors.tweet_id
		WHERE status = 0
	""")
	for id, text in db_cursor.fetchall():
		words = get_words(text)
		if not words:
			db_cursor.execute('DELETE FROM tweet_vectors WHERE tweet_id=%s', (str(id),))
			continue

		if tweet_id % 100:
			print id + " : " + text

		set_string = []
		for i, value in enumerate(d2v.infer_vector(words, alpha=0.1, min_alpha=0.0001, steps=5)):
			set_string.append('v'+str(i)+'='+str(value))
		set_string = ','.join(set_string)

		db_cursor.execute("""
			UPDATE tweet_vectors
			SET status = 1,
			""" + set_string + """
			WHERE tweet_id = %s
		""", (str(id),))

	db_connection.commit()
	time.sleep(0.1)
