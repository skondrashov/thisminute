CREATE DATABASE IF NOT EXISTS ThisMinute;
USE ThisMinute

DROP USER IF EXISTS
	'tweet2vec'@'%',
	'pericog'@'%';

DROP TABLE IF EXISTS
	tweet_vectors,
	core_tweet_vectors;

CREATE USER
	'pericog'@'%'   IDENTIFIED BY '$PW_PERICOG';

CREATE TABLE tweet_vectors (
		tweet_id BIGINT   NOT NULL,
		status   TINYINT  NOT NULL DEFAULT 0,
		time     DATETIME NOT NULL,
		lon      DOUBLE   NOT NULL,
		lat      DOUBLE   NOT NULL,
		exact    BOOLEAN  NOT NULL,
		user     BIGINT   NOT NULL,
		text     TEXT     NOT NULL,
		features TEXT,
		PRIMARY KEY (tweet_id),
		INDEX (status),
		INDEX (time)
	);
GRANT INSERT, SELECT, UPDATE ON tweet_vectors TO 'pericog'@'%';

CREATE TABLE core_tweet_vectors (
		core_tweet_id INT  NOT NULL,
		features      TEXT,
		PRIMARY KEY (core_tweet_id)
	);
GRANT DROP, INSERT, SELECT ON core_tweet_vectors TO 'pericog'@'%';
