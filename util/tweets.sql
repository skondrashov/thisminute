CREATE EXTENSION IF NOT EXISTS postgis;
ALTER EXTENSION postgis UPDATE;

-- TODO: turn this copy/pasted boilerplate into a function call... can't figure out how
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM sentinel;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM sentinel;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM sentinel;
DROP OWNED BY sentinel;
DROP USER IF EXISTS sentinel;
CREATE USER sentinel PASSWORD '$PW_SENTINEL';

REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM archivist;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM archivist;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM archivist;
DROP OWNED BY archivist;
DROP USER IF EXISTS archivist;
CREATE USER archivist PASSWORD '$PW_ARCHIVIST';

REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM pericog;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM pericog;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM pericog;
DROP OWNED BY pericog;
DROP USER IF EXISTS pericog;
CREATE USER pericog PASSWORD '$PW_PERICOG';

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

CREATE TABLE IF NOT EXISTS tweets (
		id        BIGSERIAL,
		time      TIMESTAMP(0)     NOT NULL DEFAULT NOW(),
		geo       GEOGRAPHY(POINT) NOT NULL,
		exact     BOOLEAN          NOT NULL,
		uid       BIGINT           NOT NULL,
		text      TEXT             NOT NULL,
		PRIMARY KEY (id),
		FOREIGN KEY (source_id)
			REFERENCES sources(id)
			ON DELETE RESTRICT
	);
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS tweets_id_idx ON tweets(id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS tweets_time_idx ON tweets(time);

GRANT SELECT ON tweets TO sentinel;
GRANT INSERT ON tweets TO archivist;
GRANT SELECT ON tweets TO pericog;
GRANT USAGE ON SEQUENCE tweets_id_seq TO
	sentinel,
	archivist,
	pericog;

CREATE TABLE IF NOT EXISTS tweet_metadata (
		tweet_id    BIGINT  NOT NULL,
		final       BOOLEAN NOT NULL DEFAULT FALSE,
		learned     BOOLEAN NOT NULL,
		source      TEXT    DEFAULT NULL,
		truncated   BOOLEAN DEFAULT NULL,
		reply       BOOLEAN DEFAULT NULL,
		legible     BOOLEAN DEFAULT NULL,
		informative BOOLEAN DEFAULT NULL,
		FOREIGN KEY (tweet_id)
			REFERENCES tweets(id)
			ON DELETE CASCADE,
		FOREIGN KEY (event_id)
			REFERENCES events(id)
			ON DELETE SET NULL
	);
GRANT INSERT ON tweet_metadata TO archivist;
GRANT SELECT, INSERT, UPDATE ON tweet_metadata TO pericog;

CREATE TABLE IF NOT EXISTS tweet_associations (
		tweet_id    BIGINT  NOT NULL,
		event_id    TEXT    NOT NULL,
		association BOOLEAN NOT NULL,
		confirmed   BOOLEAN NOT NULL,
		FOREIGN KEY (tweet_id)
			REFERENCES tweets(id)
			ON DELETE CASCADE,
		FOREIGN KEY (event_id)
			REFERENCES events(id)
			ON DELETE CASCADE
	);
GRANT SELECT, INSERT ON tweet_associations TO sentinel;
GRANT SELECT, INSERT, UPDATE ON tweet_associations TO pericog;

CREATE TABLE events (
		id          TEXT,
		start_time  TIMESTAMP(0)     NOT NULL,
		in_progress BOOLEAN          NOT NULL,
		end_time    TIMESTAMP(0)     NOT NULL,
		geo         GEOGRAPHY(POINT) NOT NULL,
		r_meters    SMALLINT         NOT NULL,
		PRIMARY KEY (id)
	);
GRANT SELECT, INSERT ON events TO pericog;
