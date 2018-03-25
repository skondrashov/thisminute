CREATE EXTENSION IF NOT EXISTS postgis;
ALTER EXTENSION postgis UPDATE;

REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM pericog;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM pericog;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM pericog;
DROP OWNED BY pericog;
DROP USER IF EXISTS pericog;
CREATE USER pericog PASSWORD '$PW_PERICOG';

CREATE TABLE IF NOT EXISTS users(
		id           INET     NOT NULL,
		points       BIGINT   NOT NULL DEFAULT 0,
		banned       BOOLEAN  NOT NULL DEFAULT FALSE,
		tests_passed SMALLINT          DEFAULT NULL,
		PRIMARY KEY (id)
	);

CREATE TABLE IF NOT EXISTS models (
		id TEXT NOT NULL,
		PRIMARY KEY (id)
	);
GRANT INSERT, SELECT ON models TO pericog;

CREATE TABLE IF NOT EXISTS event_types (
		id   SERIAL,
		name TEXT UNIQUE NOT NULL,
		PRIMARY KEY (id)
	);
GRANT SELECT ON event_types TO pericog;

CREATE TABLE IF NOT EXISTS events (
		id            BIGSERIAL,
		model_id      TEXT             NOT NULL,
		final         BOOLEAN          NOT NULL DEFAULT FALSE,
		event_type_id INTEGER          NOT NULL,
		name          TEXT             NOT NULL,
		start_time    TIMESTAMP(0)     NOT NULL,
		in_progress   BOOLEAN          NOT NULL,
		end_time      TIMESTAMP(0)     NOT NULL,
		geo           GEOGRAPHY(POINT) NOT NULL,
		r_meters      INTEGER          NOT NULL,
		PRIMARY KEY (id),
		FOREIGN KEY (model_id)
			REFERENCES models(id)
			ON DELETE CASCADE,
		FOREIGN KEY (event_type_id)
			REFERENCES event_types(id)
			ON DELETE CASCADE
	);
CREATE INDEX CONCURRENTLY IF NOT EXISTS
	events_final_idx ON events(final);
GRANT DELETE, SELECT, INSERT, UPDATE ON events TO pericog;

CREATE TABLE IF NOT EXISTS tweet_labels (
		tweet_id BIGINT NOT NULL,
		text     TEXT   NOT NULL,

		-- pericog-specific rows
		model_id TEXT    NOT NULL,
		user_id  INET             DEFAULT NULL,
		final    BOOLEAN NOT NULL DEFAULT FALSE,

		-- the labels we need to acquire
		source      TEXT    DEFAULT NULL,
		truncated   BOOLEAN DEFAULT NULL,
		reply       BOOLEAN DEFAULT NULL,
		spam        BOOLEAN DEFAULT NULL,
		legible     BOOLEAN DEFAULT NULL,
		informative BOOLEAN DEFAULT NULL,
		secondhand  BOOLEAN DEFAULT NULL,
		eyewitness  BOOLEAN DEFAULT NULL,
		FOREIGN KEY (model_id)
			REFERENCES models(id)
			ON DELETE CASCADE,
		FOREIGN KEY (user_id)
			REFERENCES users(id)
			ON DELETE CASCADE
	);
CREATE INDEX CONCURRENTLY IF NOT EXISTS
	tweet_labels_final_idx ON tweet_labels(final);
GRANT DELETE, SELECT, INSERT, UPDATE ON tweet_labels TO pericog;

CREATE TABLE IF NOT EXISTS tweet_events (
		tweet_id    BIGINT  NOT NULL,
		event_id    BIGINT  NOT NULL,
		model_id    TEXT    NOT NULL,
		final       BOOLEAN NOT NULL DEFAULT FALSE,
		association BOOLEAN NOT NULL,
		FOREIGN KEY (event_id)
			REFERENCES events(id)
			ON DELETE CASCADE,
		FOREIGN KEY (model_id)
			REFERENCES models(id)
			ON DELETE CASCADE
	);
CREATE INDEX CONCURRENTLY IF NOT EXISTS
	tweet_events_tweet_id_idx ON tweet_events(tweet_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS
	tweet_events_positive_idx ON tweet_events(final, association);
GRANT DELETE, SELECT, INSERT, UPDATE ON tweet_events TO pericog;

CREATE TABLE IF NOT EXISTS whitelist(
		user_id     INET    NOT NULL,
		tweet_id    BIGINT  NOT NULL,
		property    TEXT    NOT NULL,
		FOREIGN KEY (user_id)
			REFERENCES users(id)
			ON DELETE CASCADE
	);
CREATE INDEX CONCURRENTLY IF NOT EXISTS
	whitelist_tweet_id_idx ON whitelist(tweet_id);
