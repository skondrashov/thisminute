CREATE EXTENSION IF NOT EXISTS postgis;
ALTER EXTENSION postgis UPDATE;

REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM pericog;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM pericog;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM pericog;
DROP OWNED BY pericog;
DROP USER IF EXISTS pericog;
CREATE USER pericog PASSWORD '$PW_PERICOG';

CREATE TABLE IF NOT EXISTS models (
		id TEXT NOT NULL,
		PRIMARY KEY (id)
	);
GRANT INSERT, SELECT ON models TO pericog;

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
		tweet_id    BIGINT  NOT NULL,
		model_id    TEXT    NOT NULL,
		final       BOOLEAN NOT NULL DEFAULT FALSE,
		source_id   INTEGER DEFAULT NULL,
		truncated   BOOLEAN DEFAULT NULL,
		reply       BOOLEAN DEFAULT NULL,
		legible     BOOLEAN DEFAULT NULL,
		informative BOOLEAN DEFAULT NULL,
		FOREIGN KEY (tweet_id)
			REFERENCES tweets(id)
			ON DELETE CASCADE,
		FOREIGN KEY (source_id)
			REFERENCES sources(id)
			ON DELETE SET NULL,
		FOREIGN KEY (model_id)
			REFERENCES models(id)
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
		FOREIGN KEY (tweet_id)
			REFERENCES tweets(id)
			ON DELETE CASCADE,
		FOREIGN KEY (event_id)
			REFERENCES events(id)
			ON DELETE CASCADE,
		FOREIGN KEY (model_id)
			REFERENCES models(id)
			ON DELETE CASCADE
	);
CREATE INDEX CONCURRENTLY IF NOT EXISTS
	tweet_events_positive_idx ON tweet_events(final, association);
GRANT DELETE, SELECT, INSERT, UPDATE ON tweet_events TO pericog;
