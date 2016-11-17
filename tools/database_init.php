#!/usr/bin/env php
<?php
$root_password            = file_get_contents("/srv/auth/root.pw");
$archivist_password       = file_get_contents("/srv/auth/daemons/archivist.pw");
$pericog_limited_password = file_get_contents("/srv/auth/daemons/pericog_limited.pw");
$pericog_admin_password   = file_get_contents("/srv/auth/daemons/pericog_admin.pw");

$db = new mysqli("localhost", "root", $root_password);
$queries = [
        "CREATE USER 'archivist'@'localhost'       IDENTIFIED BY '{$archivist_password}'",
        "CREATE USER 'pericog_limited'@'localhost' IDENTIFIED BY '{$pericog_limited_password}'",
        "CREATE USER 'pericog_admin'@'localhost'   IDENTIFIED BY '{$pericog_admin_password}'",

        "CREATE DATABASE ThisMinute",

        "CREATE TABLE ThisMinute.tweets (
                lon   DOUBLE    NOT NULL,
                lat   DOUBLE    NOT NULL,
                exact BOOLEAN   NOT NULL,
                text  TEXT      NOT NULL,
                user  BIGINT    NOT NULL,
                time  TIMESTAMP NOT NULL DEFAULT NOW()
            )",
        "GRANT INSERT ON ThisMinute.tweets TO 'archivist'@'localhost'",
        "GRANT SELECT ON ThisMinute.tweets TO 'pericog_admin'@'localhost'",

        "CREATE TABLE ThisMinute.events (
                id         BIGINT    NOT NULL,
                lon        DOUBLE    NOT NULL,
                lat        DOUBLE    NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time   TIMESTAMP NOT NULL,
                users      INT       NOT NULL,
                PRIMARY KEY (id)
            )",
        "GRANT ALTER, CREATE, DROP, INSERT, SELECT ON ThisMinute.events TO 'pericog_admin'@'localhost'",

        "CREATE TABLE ThisMinute.events_new LIKE ThisMinute.events",
        "GRANT ALTER, CREATE, DROP, INSERT ON ThisMinute.events_new TO 'pericog_admin'@'localhost'",

        "CREATE TABLE ThisMinute.events_old LIKE ThisMinute.events",
        "GRANT CREATE, DROP, INSERT ON ThisMinute.events_old TO 'pericog_admin'@'localhost'",
        "DROP TABLE ThisMinute.events_old",

        "CREATE TABLE ThisMinute.event_tweets (
                event_id BIGINT    NOT NULL,
                time     TIMESTAMP NOT NULL,
                lon      DOUBLE    NOT NULL,
                lat      DOUBLE    NOT NULL,
                exact    BOOLEAN   NOT NULL,
                text     TEXT      NOT NULL,
                FOREIGN KEY (event_id)
                    REFERENCES ThisMinute.events(id)
                    ON DELETE CASCADE
            )",
        "GRANT ALTER, CREATE, DROP, INSERT, SELECT ON ThisMinute.event_tweets TO 'pericog_admin'@'localhost'",

        "CREATE TABLE ThisMinute.event_tweets_new LIKE ThisMinute.event_tweets",
        "GRANT ALTER, CREATE, DROP ON ThisMinute.event_tweets_new TO 'pericog_admin'@'localhost'",
        "GRANT INSERT ON ThisMinute.event_tweets_new TO 'pericog_limited'@'localhost'",

        "CREATE TABLE ThisMinute.event_tweets_old LIKE ThisMinute.event_tweets",
        "GRANT CREATE, DROP, INSERT ON ThisMinute.event_tweets_old TO 'pericog_admin'@'localhost'",
        "DROP TABLE ThisMinute.event_tweets_old",
    ];
foreach ($queries as $query)
    echo "$query : \n RESULT: " . var_export($db->query($query), true) . "\n\n";
