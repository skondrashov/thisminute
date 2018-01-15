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

CREATE TABLE IF NOT EXISTS sources (
		id   SERIAL,
		name TEXT UNIQUE NOT NULL,
		PRIMARY KEY (id)
	);

CREATE TABLE IF NOT EXISTS events (
		id          SERIAL,
		human       BOOLEAN          NOT NULL,
		name        TEXT             NOT NULL,
		start_time  TIMESTAMP(0)     NOT NULL,
		in_progress BOOLEAN          NOT NULL,
		end_time    TIMESTAMP(0)     NOT NULL,
		geo         GEOGRAPHY(POINT) NOT NULL,
		r_meters    INTEGER          NOT NULL,
		PRIMARY KEY (id)
	);

CREATE TABLE IF NOT EXISTS tweets (
		id    BIGSERIAL,
		time  TIMESTAMP(0)     NOT NULL DEFAULT NOW(),
		geo   GEOGRAPHY(POINT) NOT NULL,
		exact BOOLEAN          NOT NULL,
		uid   BIGINT           NOT NULL,
		text  TEXT             NOT NULL,
		PRIMARY KEY (id)
	);
CREATE INDEX CONCURRENTLY IF NOT EXISTS tweets_time_idx ON tweets(time);

GRANT SELECT ON tweets TO sentinel;
GRANT INSERT ON tweets TO archivist;
GRANT SELECT ON tweets TO pericog;
GRANT USAGE ON SEQUENCE tweets_id_seq TO
	sentinel,
	archivist,
	pericog;

CREATE TABLE IF NOT EXISTS tweet_labels (
		tweet_id          BIGINT  NOT NULL,
		final             BOOLEAN NOT NULL DEFAULT FALSE,
		human             BOOLEAN NOT NULL,
		tweet_source_id   INTEGER DEFAULT NULL,
		tweet_truncated   BOOLEAN DEFAULT NULL,
		tweet_reply       BOOLEAN DEFAULT NULL,
		tweet_legible     BOOLEAN DEFAULT NULL,
		tweet_informative BOOLEAN DEFAULT NULL,
		FOREIGN KEY (tweet_id)
			REFERENCES tweets(id)
			ON DELETE CASCADE,
		FOREIGN KEY (tweet_source_id)
			REFERENCES sources(id)
			ON DELETE SET NULL
	);
GRANT INSERT ON tweet_labels TO archivist;
GRANT SELECT, INSERT, UPDATE ON tweet_labels TO pericog;

CREATE TABLE IF NOT EXISTS tweet_events (
		tweet_id    BIGINT  NOT NULL,
		event_id    INTEGER NOT NULL,
		final       BOOLEAN NOT NULL DEFAULT FALSE,
		human       BOOLEAN NOT NULL,
		association BOOLEAN NOT NULL,
		FOREIGN KEY (tweet_id)
			REFERENCES tweets(id)
			ON DELETE CASCADE,
		FOREIGN KEY (event_id)
			REFERENCES events(id)
			ON DELETE CASCADE
	);
