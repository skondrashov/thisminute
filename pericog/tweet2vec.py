import logging, time, json
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
batch_start_time = int(config.get('timing', 'start'))
batch_time_range = int(config.get('timing', 'period'))

db_tweets_connection = mysql.connector.connect(
		user='tweet2vec',
		password=open('/srv/auth/mysql/tweet2vec.pw').read(),
		host='localhost',
		database='ThisMinute'
	)
db_tweets_cursor = db_tweets_connection.cursor()

db_pericog_connection = mysql.connector.connect(
		user='tweet2vec',
		password=open('/srv/auth/mysql/tweet2vec.pw').read(),
		host=TARGET_IP,
		database='ThisMinute'
	)
db_pericog_cursor = db_pericog_connection.cursor()

def get_words(tweet):
	tweet = re.sub('((\B@)|(\\bhttps?:\/\/))[^\\s]+', " ", tweet)
	tweet = re.sub('[^\w]+', " ", tweet)
	tweet = tweet.lower().strip()
	tweet = unicode(unidecode(tweet))
	return tweet.split()

print "Loading tweets"
db_tweets_cursor.execute("SELECT tweet_id, text FROM training_tweets")

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

print "Getting core vectors"
db_pericog_cursor.execute("TRUNCATE core_tweet_vectors")
db_tweets_cursor.execute("SELECT id, text FROM core_tweets")
for id, text in db_tweets_cursor.fetchall():
	vector = d2v.infer_vector(get_words(text), alpha=0.1, min_alpha=0.0001, steps=5)

	db_pericog_cursor.execute("""
		INSERT INTO core_tweet_vectors (`core_tweet_id`, `vector`)
		VALUES (%s, %s)
	""", (id, json.dumps(vector)))

db_pericog_connection.commit()

print "Waiting for pericog"
while True:
	db_pericog_cursor.execute('DELETE FROM tweet_vectors WHERE status = 1')

	db_pericog_cursor.execute("SELECT UNIX_TIMESTAMP(MAX(time)) - UNIX_TIMESTAMP(MIN(time)) AS time_range FROM tweet_vectors")
	time_range = db_pericog_cursor.fetchone()
	if time_range > batch_time_range * 2:
		continue

	db_tweets_cursor.execute("""
		SELECT * FROM tweets WHERE time BETWEEN FROM_UNIXTIME({0}) AND FROM_UNIXTIME({0}+{1})
	""", (batch_start_time, batch_time_range));
	batch_start_time += batch_time_range

	for id, time, lon, lat, exact, user, text in db_tweets_cursor.fetchall():
		words = get_words(text)
		if not words:
			continue

		features = json.dumps(d2v.infer_vector(words, alpha=0.1, min_alpha=0.0001, steps=5))
		db_pericog_cursor.execute("""
			INSERT INTO tweet_vectors (`tweet_id`, `time`, `lon`, `lat`, `exact`, `user`, `text`, `features`)
			VALUES %s, %s, %s, %s, %s, %s, %s, %s
		""", (id, time, lon, lat, exact, user, text, features))

	db_pericog_connection.commit()

	time.sleep(5)
