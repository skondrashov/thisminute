CREATE DATABASE IF NOT EXISTS ThisMinute;
USE ThisMinute

DROP USER IF EXISTS
	'pericog'@'%';

CREATE USER
	'pericog'@'%'   IDENTIFIED BY '$PW_PERICOG';

CREATE TABLE IF NOT EXISTS events (
		id          SERIAL,
		model_id    TEXT             NOT NULL,
		final       BOOLEAN          NOT NULL DEFAULT FALSE,
		name        TEXT             NOT NULL,
		start_time  TIMESTAMP(0)     NOT NULL,
		in_progress BOOLEAN          NOT NULL,
		end_time    TIMESTAMP(0)     NOT NULL,
		geo         GEOGRAPHY(POINT) NOT NULL,
		r_meters    INTEGER          NOT NULL,
		PRIMARY KEY (id)
	);

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
			ON DELETE SET NULL
	);
CREATE INDEX CONCURRENTLY IF NOT EXISTS tweet_labels_final_idx ON tweet_labels(final);

GRANT INSERT ON tweet_labels TO archivist;
GRANT SELECT, INSERT, UPDATE ON tweet_labels TO pericog;

CREATE TABLE IF NOT EXISTS tweet_events (
		tweet_id    BIGINT  NOT NULL,
		event_id    INTEGER NOT NULL,
		model_id    TEXT    NOT NULL,
		final       BOOLEAN NOT NULL DEFAULT FALSE,
		association BOOLEAN NOT NULL,
		FOREIGN KEY (tweet_id)
			REFERENCES tweets(id)
			ON DELETE CASCADE,
		FOREIGN KEY (event_id)
			REFERENCES events(id)
			ON DELETE CASCADE
	);

CREATE TABLE IF NOT EXISTS models (
		id TEXT NOT NULL
	);
