from __future__ import print_function
from __future__ import division

import timeit

import ConfigParser
import mysql.connector

config = ConfigParser.RawConfigParser()
config.read('/srv/config.ini')

ACTIVE_DB_NAME    = config.get('connections', 'active')
ACTIVE_DB_ADDRESS = config.get('connections', ACTIVE_DB_NAME)

print("Connecting to ", ACTIVE_DB_NAME, " at ", ACTIVE_DB_ADDRESS)
db_tweets_connection = mysql.connector.connect(
		user='pericog',
		password=open('/srv/auth/mysql/pericog.pw').read(),
		host=ACTIVE_DB_ADDRESS,
		database='ThisMinute'
	)
db_tweets_cursor = db_tweets_connection.cursor()

print("Connecting to ", ACTIVE_DB_NAME, " at ", ACTIVE_DB_ADDRESS)
db_tweets_connection1 = mysql.connector.connect(
		user='pericog',
		password=open('/srv/auth/mysql/pericog.pw').read(),
		host=ACTIVE_DB_ADDRESS,
		database='ThisMinute'
	)
db_tweets_cursor1 = db_tweets_connection1.cursor()

def benchmark1():
	db_tweets_cursor.execute("""
			SELECT MAX(id) FROM tweets
		""")
	db_tweets_cursor.fetchall()
def benchmark2():
	db_tweets_cursor1.execute("""
			SELECT id FROM tweets ORDER BY id LIMIT 1
		""")
	db_tweets_cursor1.fetchall()

if __name__ == "__main__":
	print(timeit.timeit("benchmark1()", number=100, setup="from __main__ import benchmark1"))
	print(timeit.timeit("benchmark2()", number=100, setup="from __main__ import benchmark2"))
