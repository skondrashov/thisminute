CREATE EXTENSION IF NOT EXISTS postgis;
ALTER EXTENSION postgis UPDATE;

-- TODO: turn this copy/pasted boilerplate into a function call... can't figure out how
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

REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM sentinel;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM sentinel;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM sentinel;
DROP OWNED BY sentinel;
DROP USER IF EXISTS sentinel;
CREATE USER sentinel PASSWORD '$PW_SENTINEL';

-- using this with ON UPDATE CASCADE allows us to easily change source names
CREATE TABLE IF NOT EXISTS sources (
      id TEXT,
      PRIMARY KEY (id)
   );

CREATE TABLE IF NOT EXISTS event_types (
      id   SERIAL,
      name TEXT UNIQUE NOT NULL,
      PRIMARY KEY (id)
   );
GRANT SELECT ON event_types TO pericog;

CREATE TABLE IF NOT EXISTS events (
      id            BIGINT,
      event_type_id INTEGER          DEFAULT NULL,
      name          TEXT             DEFAULT NULL,
      start_time    TIMESTAMP(0)     NOT NULL,
      in_progress   BOOLEAN          NOT NULL,
      end_time      TIMESTAMP(0)     NOT NULL,
      geo           GEOGRAPHY(POINT) NOT NULL,
      r_meters      INTEGER          NOT NULL,
      PRIMARY KEY (id),
      FOREIGN KEY (event_type_id)
         REFERENCES event_types(id)
         ON DELETE SET NULL
   );
GRANT INSERT, SELECT, UPDATE ON events TO pericog;
GRANT SELECT ON events TO sentinel;

CREATE TABLE IF NOT EXISTS tweets (
      id    BIGSERIAL,
      time  TIMESTAMP(0)     NOT NULL DEFAULT NOW(),
      geo   GEOGRAPHY(POINT) NOT NULL,
      exact BOOLEAN          NOT NULL,
      uid   BIGINT           NOT NULL,
      text  TEXT             NOT NULL,
      PRIMARY KEY (id)
   );
CREATE INDEX CONCURRENTLY IF NOT EXISTS
   tweets_time_idx ON tweets(time);
GRANT INSERT ON tweets TO archivist;
GRANT SELECT ON tweets TO pericog;
GRANT SELECT ON tweets TO sentinel;
GRANT USAGE ON SEQUENCE tweets_id_seq TO
   sentinel,
   archivist,
   pericog;

CREATE TABLE IF NOT EXISTS tweet_properties (
      tweet_id            BIGINT  UNIQUE NOT NULL,
      crowdflower         BOOLEAN DEFAULT NULL,
      source              TEXT    DEFAULT NULL,
      truncated           BOOLEAN DEFAULT NULL,
      reply               BOOLEAN DEFAULT NULL,
      spam                BOOLEAN DEFAULT NULL,
      legible             BOOLEAN DEFAULT NULL,
      informative         BOOLEAN DEFAULT NULL,
      secondhand          BOOLEAN DEFAULT NULL,
      eyewitness          BOOLEAN DEFAULT NULL,
      tweet2vec_train     BOOLEAN DEFAULT FALSE,
      random_forest_train BOOLEAN DEFAULT FALSE,
      tagger_train        BOOLEAN DEFAULT FALSE,
      FOREIGN KEY (tweet_id)
         REFERENCES tweets(id)
         ON DELETE CASCADE,
      FOREIGN KEY (source)
         REFERENCES sources(id)
         ON UPDATE CASCADE
         ON DELETE SET NULL
   );
GRANT INSERT ON tweet_properties TO archivist;
GRANT SELECT, INSERT, UPDATE ON tweet_properties TO pericog;
GRANT SELECT, INSERT, UPDATE ON tweet_properties TO sentinel;

CREATE TABLE IF NOT EXISTS tweet_events (
      tweet_id BIGINT NOT NULL,
      event_id BIGINT DEFAULT NULL,
      PRIMARY KEY (tweet_id, event_id),
      FOREIGN KEY (tweet_id)
         REFERENCES tweets(id)
         ON DELETE CASCADE,
      FOREIGN KEY (event_id)
         REFERENCES events(id)
         ON DELETE CASCADE
   );
GRANT SELECT, INSERT, UPDATE ON tweet_events TO pericog;
GRANT SELECT ON tweet_events TO sentinel;

CREATE TABLE IF NOT EXISTS tweet_votes (
      tweet_id    BIGINT  NOT NULL,
      user_ip     INET    NOT NULL,

      spam        BOOLEAN DEFAULT NULL,
      fiction     BOOLEAN DEFAULT NULL,
      poetry      BOOLEAN DEFAULT NULL,
      use         BOOLEAN DEFAULT NULL,
      event       BOOLEAN DEFAULT NULL,
      disaster    BOOLEAN DEFAULT NULL,
      personal    BOOLEAN DEFAULT NULL,
      eyewitness  BOOLEAN DEFAULT NULL,
      secondhand  BOOLEAN DEFAULT NULL,
      breaking    BOOLEAN DEFAULT NULL,
      informative BOOLEAN DEFAULT NULL,

      legible     BOOLEAN DEFAULT NULL,
      PRIMARY KEY (tweet_id, user_ip),
      FOREIGN KEY (tweet_id)
         REFERENCES tweets(id)
         ON DELETE CASCADE
   );
GRANT SELECT, INSERT, UPDATE ON tweet_votes TO pericog;
GRANT SELECT, INSERT, UPDATE ON tweet_votes TO sentinel;
