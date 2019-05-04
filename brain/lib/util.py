from __future__ import print_function
from __future__ import division

import re
from unidecode import unidecode
def get_words(tweet):
	tweet = re.sub('((\B@)|(\\bhttps?:\/\/))[^\\s]+', " ", tweet)
	tweet = re.sub('[^\w]+', " ", tweet)
	tweet = tweet.lower().strip()
	tweet = unicode(unidecode(tweet))
	return tweet.split()

import psycopg2
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
def db_tweets_connect(username, hostname, test=False):
	print("Connecting to database at", hostname)
	try:
		return psycopg2.connect(
				user=username,
				password=open('/srv/auth/sql/' + username + '.pw').read(),
				host=hostname,
				database='thisminute' + ('-test' if test else ''),
				connect_timeout=5
			)
	except:
		print("Failed to connect to", hostname)
		raise

import configparser
parser = configparser.RawConfigParser()
parser.read('/srv/config.ini')
def config(section, option):
	value = parser.get(section, option)
	try:
		return int(value)
	except:
		return value
