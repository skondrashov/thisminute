CREATE EXTENSION postgis;
ALTER EXTENSION postgis UPDATE;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM pericog;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM pericog;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM pericog;
DROP OWNED BY pericog;
DROP USER IF EXISTS pericog;

DROP TABLE IF EXISTS
	tweet_vectors,
	core_tweet_vectors;

CREATE USER pericog PASSWORD '$PW_PERICOG';

CREATE TABLE tweet_vectors (
		tweet_id BIGINT           NOT NULL,
		status   SMALLINT         NOT NULL DEFAULT 0,
		time     TIMESTAMP(0)     NOT NULL,
		geo      GEOGRAPHY(POINT) NOT NULL,
		exact    BOOLEAN          NOT NULL,
		uid      BIGINT           NOT NULL,
		text     TEXT             NOT NULL,
		features TEXT,
		PRIMARY KEY (tweet_id)
	);
GRANT DELETE, INSERT, SELECT, UPDATE ON tweet_vectors TO pericog;

CREATE TABLE core_tweet_vectors (
		core_tweet_id INT  NOT NULL,
		features      TEXT,
		PRIMARY KEY (core_tweet_id)
	);
GRANT DROP, INSERT, SELECT ON core_tweet_vectors TO pericog;
