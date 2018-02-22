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
		id    BIGSERIAL,
		time  TIMESTAMP(0)     NOT NULL DEFAULT NOW(),
		geo   GEOGRAPHY(POINT) NOT NULL,
		exact BOOLEAN          NOT NULL,
		uid   BIGINT           NOT NULL,
		text  TEXT             NOT NULL,
		PRIMARY KEY (id)
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

CREATE TABLE IF NOT EXISTS tweets_rus () INHERITS (tweets);
GRANT SELECT ON tweets_rus TO sentinel;
GRANT INSERT ON tweets_rus TO archivist;
GRANT SELECT ON tweets_rus TO pericog;
