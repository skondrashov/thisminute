#!/usr/bin/python
from __future__ import print_function
from __future__ import division

import numpy
import tensorflow

from gensim.models import Doc2Vec
from gensim.models.doc2vec import TaggedDocument

from tensorflow.contrib.tensor_forest.client import random_forest
from tensorflow.contrib.tensor_forest.python import tensor_forest
from tensorflow.python.estimator.inputs import numpy_io

from tensorflow.contrib.learn.python.learn import metric_spec
from tensorflow.contrib.tensor_forest.client import eval_metrics

import logging, time

import ConfigParser
import mysql.connector

import re
from unidecode import unidecode
import os.path

tensorflow.logging.set_verbosity(tensorflow.logging.ERROR)
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

print("Connecting to tweets")
ACTIVE_DB_NAME = config.get('connections', 'active')
db_tweets_connection = mysql.connector.connect(
		user='pericog',
		password=open('/srv/auth/mysql/pericog.pw').read(),
		host=config.get('connections', ACTIVE_DB_NAME),
		database='ThisMinute'
	)
db_tweets_cursor = db_tweets_connection.cursor()

def get_words(tweet):
	tweet = re.sub('((\B@)|(\\bhttps?:\/\/))[^\\s]+', " ", tweet)
	tweet = re.sub('[^\w]+', " ", tweet)
	tweet = tweet.lower().strip()
	tweet = unicode(unidecode(tweet))
	return tweet.split()

def get_vector(tweet):
	return t2v.infer_vector(get_words(tweet), alpha=0.1, min_alpha=0.0001, steps=5)

t2v = Doc2Vec.load('/srv/tweet2vec.model')

anchor = get_vector(u"Fire in Santa Paula tonight. My view of it from Xmas tree farm")

print("Pulling tweets for tagging")
db_tweets_cursor.execute("""
		SELECT tweet_id, text
		FROM tagged_tweets
		WHERE
			master_sentiment IS NULL
	""")

tweets = []
for id, text in db_tweets_cursor.fetchall():
	vec = get_vector(text)
	distance = numpy.dot(anchor, vec) / (numpy.linalg.norm(anchor)*numpy.linalg.norm(vec))

	temp = unicode(unidecode(text))
	if temp[0] == '@' or temp[-23:-11] == 'https://t.co':
		continue

	tweets.append({'id': id, 'text': text, 'distance': distance, 'processed': False})

while True:
	index = 18294812948
	min_distance = 999999
	for i, tweet in enumerate(tweets):
		if not tweet['processed'] and tweet['distance'] < min_distance:
			min_distance = tweet['distance']
			text = tweet['text']
			index = i

	tweets[index]['processed'] = True

	print()
	print(text)
	value = raw_input("y = we want to detect this, n = nah: ")
	if value not in ['y', 'n']:
		continue

	value = 1 if value == 'y' else 0
	db_tweets_cursor.execute("""
		UPDATE tagged_tweets SET master_sentiment=%s WHERE tweet_id=%s
	""", (value, tweets[index]['id']))
	db_tweets_connection.commit()
