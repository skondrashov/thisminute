CREATE DATABASE IF NOT EXISTS ThisMinute;
USE ThisMinute

DROP USER IF EXISTS
	'sentinel'@'%',
	'archivist'@'%',
	'pericog'@'%';

/******************************************
* DO NOT EVER:                            *
* - DROP DATABASE ThisMinute              *
* - DROP TABLE ThisMinute.tweets          *
* - DROP TABLE ThisMinute.core_tweets     *
* - DROP TABLE ThisMinute.training_tweets *
******************************************/
DROP TABLE IF EXISTS
	event_tweets,
	event_tweets_new,
	event_tweets_old,
	events,
	events_new,
	events_old;

CREATE USER
	'sentinel'@'%'  IDENTIFIED BY '$PW_SENTINEL',
	'archivist'@'%' IDENTIFIED BY '$PW_ARCHIVIST',
	'pericog'@'%'   IDENTIFIED BY '$PW_PERICOG';

CREATE TABLE IF NOT EXISTS tweets (
		id    BIGINT   NOT NULL AUTO_INCREMENT,
		time  DATETIME NOT NULL DEFAULT NOW(),
		lon   DOUBLE   NOT NULL,
		lat   DOUBLE   NOT NULL,
		exact BOOLEAN  NOT NULL,
		user  BIGINT   NOT NULL,
		text  TEXT     NOT NULL,
		INDEX (time),
		PRIMARY KEY (id)
	);
GRANT SELECT ON tweets TO 'sentinel'@'%';
GRANT INSERT ON tweets TO 'archivist'@'%';
GRANT SELECT ON tweets TO 'pericog'@'%';

CREATE TABLE IF NOT EXISTS core_tweets (
		id   INT  NOT NULL AUTO_INCREMENT,
		text TEXT NOT NULL,
		PRIMARY KEY (id)
	);
GRANT SELECT ON core_tweets TO 'pericog'@'%';

CREATE TABLE IF NOT EXISTS training_tweets (
		id      BIGINT  NOT NULL,
		text    TEXT    NOT NULL,
		frantic BOOLEAN DEFAULT NULL,
		PRIMARY KEY (id)
	);
GRANT SELECT ON training_tweets TO 'pericog'@'%';

CREATE TABLE IF NOT EXISTS tagged_tweets (
		tweet_id  BIGINT   NOT NULL AUTO_INCREMENT,
		time      DATETIME NOT NULL,
		lon       DOUBLE   NOT NULL,
		lat       DOUBLE   NOT NULL,
		exact     BOOLEAN  NOT NULL,
		text      TEXT     NOT NULL,
		reply     BOOLEAN  NOT NULL,
		master_sentiment BOOLEAN DEFAULT NULL,
		frantic   BOOLEAN DEFAULT NULL,
		proximity TINYINT DEFAULT NULL,
		relevance TINYINT DEFAULT NULL,
		FOREIGN KEY (tweet_id)
			REFERENCES tweets (id)
			ON DELETE CASCADE
	);
GRANT SELECT, INSERT, UPDATE ON tagged_tweets TO 'pericog'@'%';

CREATE TABLE events (
		id         BIGINT   NOT NULL,
		lon        DOUBLE   NOT NULL,
		lat        DOUBLE   NOT NULL,
		start_time DATETIME NOT NULL,
		end_time   DATETIME NOT NULL,
		users      INT      NOT NULL,
		PRIMARY KEY (id)
	);
GRANT SELECT ON events TO 'sentinel'@'%';
GRANT ALTER, CREATE, DROP, INSERT, SELECT ON events TO 'pericog'@'%';

CREATE TABLE events_new LIKE events;
GRANT ALTER, CREATE, DROP, INSERT ON events_new TO 'pericog'@'%';

CREATE TABLE events_old LIKE events;
GRANT CREATE, DROP, INSERT ON events_old TO 'pericog'@'%';

CREATE TABLE event_tweets (
		event_id BIGINT   NOT NULL,
		time     DATETIME NOT NULL,
		lon      DOUBLE   NOT NULL,
		lat      DOUBLE   NOT NULL,
		exact    BOOLEAN  NOT NULL,
		text     TEXT     NOT NULL,
		FOREIGN KEY (event_id)
			REFERENCES events (id)
			ON DELETE CASCADE
	);
GRANT SELECT ON event_tweets TO 'sentinel'@'%';
GRANT ALTER, CREATE, DROP, INSERT, SELECT ON event_tweets TO 'pericog'@'%';

CREATE TABLE event_tweets_new LIKE event_tweets;
GRANT ALTER, CREATE, DROP, INSERT ON event_tweets_new TO 'pericog'@'%';

CREATE TABLE event_tweets_old LIKE event_tweets;
GRANT CREATE, DROP, INSERT ON event_tweets_old TO 'pericog'@'%';
