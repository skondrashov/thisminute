CREATE EXTENSION postgis;
ALTER EXTENSION postgis UPDATE;

REASSIGN OWNED BY sentinel TO postgres;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM sentinel;
DROP OWNED BY sentinel;
REASSIGN OWNED BY archivist TO postgres;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM archivist;
DROP OWNED BY archivist;
REASSIGN OWNED BY pericog TO postgres;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM pericog;
DROP OWNED BY pericog;
DROP USER IF EXISTS
	sentinel,
	archivist,
	pericog;

/******************************************
* DO NOT EVER:                            *
* - DROP DATABASE thisminute              *
* - DROP TABLE thisminute.tweets          *
* - DROP TABLE thisminute.tweets_*        *
* - DROP TABLE thisminute.core_tweets     *
* - DROP TABLE thisminute.training_tweets *
******************************************/
DROP TABLE IF EXISTS
	event_tweets,
	event_tweets_new,
	event_tweets_old,
	events,
	events_new,
	events_old;

CREATE USER sentinel  PASSWORD '$PW_SENTINEL';
CREATE USER archivist PASSWORD '$PW_ARCHIVIST';
CREATE USER pericog   PASSWORD '$PW_PERICOG';

CREATE TABLE IF NOT EXISTS tweets (
		id    BIGSERIAL,
		time  TIMESTAMP(0) NOT NULL DEFAULT NOW(),
		geo   GEOGRAPHY(POINT) NOT NULL,
		exact BOOLEAN  NOT NULL,
		uid   BIGINT   NOT NULL,
		text  TEXT     NOT NULL,
		PRIMARY KEY (id)
	);

GRANT SELECT ON tweets TO sentinel;
GRANT INSERT ON tweets TO archivist;
GRANT SELECT ON tweets TO pericog;
GRANT USAGE ON SEQUENCE tweets_id_seq TO
	sentinel,
	archivist,
	pericog;

CREATE TABLE IF NOT EXISTS tweets_rus () INHERITS (tweets);
GRANT SELECT ON tweets_rus TO sentinel;
GRANT INSERT ON tweets_rus TO archivist;
GRANT SELECT ON tweets_rus TO pericog;

-- CREATE TABLE IF NOT EXISTS core_tweets (
-- 		id   SERIAL,
-- 		text TEXT NOT NULL,
-- 		PRIMARY KEY (id)
-- 	);
-- GRANT SELECT ON core_tweets TO pericog;

-- CREATE TABLE IF NOT EXISTS training_tweets (
-- 		id      BIGINT  NOT NULL,
-- 		text    TEXT    NOT NULL,
-- 		frantic BOOLEAN DEFAULT NULL,
-- 		PRIMARY KEY (id)
-- 	);
-- GRANT SELECT ON training_tweets TO pericog;

-- CREATE TABLE IF NOT EXISTS tagged_tweets (
-- 		tweet_id  BIGINT   NOT NULL AUTO_INCREMENT,
-- 		time      DATETIME NOT NULL,
-- 		lon       DOUBLE   NOT NULL,
-- 		lat       DOUBLE   NOT NULL,
-- 		exact     BOOLEAN  NOT NULL,
-- 		text      TEXT     NOT NULL,
-- 		reply     BOOLEAN  NOT NULL,
-- 		master_sentiment BOOLEAN DEFAULT NULL,
-- 		frantic   BOOLEAN DEFAULT NULL,
-- 		proximity TINYINT DEFAULT NULL,
-- 		relevance TINYINT DEFAULT NULL,
-- 		FOREIGN KEY (tweet_id)
-- 			REFERENCES tweets (id)
-- 			ON DELETE CASCADE
-- 	);
-- GRANT SELECT, INSERT, UPDATE ON tagged_tweets TO 'pericog'@'%';

-- CREATE TABLE events (
-- 		id         BIGINT   NOT NULL,
-- 		lon        DOUBLE   NOT NULL,
-- 		lat        DOUBLE   NOT NULL,
-- 		start_time DATETIME NOT NULL,
-- 		end_time   DATETIME NOT NULL,
-- 		users      INT      NOT NULL,
-- 		PRIMARY KEY (id)
-- 	);
-- GRANT SELECT ON events TO 'sentinel'@'%';
-- GRANT ALTER, CREATE, DROP, INSERT, SELECT ON events TO 'pericog'@'%';

-- CREATE TABLE events_new LIKE events;
-- GRANT ALTER, CREATE, DROP, INSERT ON events_new TO 'pericog'@'%';

-- CREATE TABLE events_old LIKE events;
-- GRANT CREATE, DROP, INSERT ON events_old TO 'pericog'@'%';

-- CREATE TABLE event_tweets (
-- 		event_id BIGINT   NOT NULL,
-- 		time     DATETIME NOT NULL,
-- 		lon      DOUBLE   NOT NULL,
-- 		lat      DOUBLE   NOT NULL,
-- 		exact    BOOLEAN  NOT NULL,
-- 		text     TEXT     NOT NULL,
-- 		FOREIGN KEY (event_id)
-- 			REFERENCES events (id)
-- 			ON DELETE CASCADE
-- 	);
-- GRANT SELECT ON event_tweets TO 'sentinel'@'%';
-- GRANT ALTER, CREATE, DROP, INSERT, SELECT ON event_tweets TO 'pericog'@'%';

-- CREATE TABLE event_tweets_new LIKE event_tweets;
-- GRANT ALTER, CREATE, DROP, INSERT ON event_tweets_new TO 'pericog'@'%';

-- CREATE TABLE event_tweets_old LIKE event_tweets;
-- GRANT CREATE, DROP, INSERT ON event_tweets_old TO 'pericog'@'%';
