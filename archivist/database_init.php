#!/usr/bin/env php
<?php
// this file uses spaces for indentation to make the queries easier to write

$config = parse_ini_file("/srv/config/daemons.ini", true);
$db_name = $config['connections']['active'];

$root_password            = $argv[1];
$archivist_password       = file_get_contents("/srv/auth/daemons/archivist.pw");
$pericog_limited_password = file_get_contents("/srv/auth/daemons/pericog_limited.pw");
$pericog_admin_password   = file_get_contents("/srv/auth/daemons/pericog_admin.pw");

$queries = [
        "DROP USER IF EXISTS
            'archivist'@'%',
            'pericog_limited'@'%',
            'pericog_admin'@'%'
            ",

        "CREATE USER
            'archivist'@'%'       IDENTIFIED BY '{$archivist_password}',
            'pericog_limited'@'%' IDENTIFIED BY '{$pericog_limited_password}',
            'pericog_admin'@'%'   IDENTIFIED BY '{$pericog_admin_password}'
            ",

        "CREATE DATABASE ThisMinute",

        // ******************************
        // DO NOT EVER:
        // - DROP DATABASE ThisMinute
        // - DROP TABLE ThisMinute.tweets
        // ******************************
        "DROP TABLE IF EXISTS
            ThisMinute.events,
            ThisMinute.events_new,
            ThisMinute.events_old,
            ThisMinute.event_tweets,
            ThisMinute.event_tweets_new,
            ThisMinute.event_tweets_old
            ",

        "CREATE TABLE ThisMinute.tweets (
                time  DATETIME NOT NULL DEFAULT NOW(),
                lon   DOUBLE   NOT NULL,
                lat   DOUBLE   NOT NULL,
                exact BOOLEAN  NOT NULL,
                user  BIGINT   NOT NULL,
                text  TEXT     NOT NULL,
                INDEX (time)
            )",

        "GRANT INSERT ON ThisMinute.tweets TO 'archivist'@'%'",
        "GRANT SELECT ON ThisMinute.tweets TO 'pericog_admin'@'%'",

        "CREATE TABLE ThisMinute.events (
                id         BIGINT   NOT NULL,
                lon        DOUBLE   NOT NULL,
                lat        DOUBLE   NOT NULL,
                start_time DATETIME NOT NULL,
                end_time   DATETIME NOT NULL,
                users      INT      NOT NULL,
                PRIMARY KEY (id)
            )",
        "GRANT ALTER, CREATE, DROP, INSERT, SELECT ON ThisMinute.events TO 'pericog_admin'@'%'",

        "CREATE TABLE ThisMinute.events_new LIKE ThisMinute.events",
        "GRANT ALTER, CREATE, DROP, INSERT ON ThisMinute.events_new TO 'pericog_admin'@'%'",

        "CREATE TABLE ThisMinute.events_old LIKE ThisMinute.events",
        "GRANT CREATE, DROP, INSERT ON ThisMinute.events_old TO 'pericog_admin'@'%'",

        "CREATE TABLE ThisMinute.event_tweets (
                event_id BIGINT   NOT NULL,
                time     DATETIME NOT NULL,
                lon      DOUBLE   NOT NULL,
                lat      DOUBLE   NOT NULL,
                exact    BOOLEAN  NOT NULL,
                text     TEXT     NOT NULL,
                FOREIGN KEY (event_id)
                    REFERENCES ThisMinute.events (id)
                    ON DELETE CASCADE
            )",
        "GRANT ALTER, CREATE, DROP, INSERT, SELECT ON ThisMinute.event_tweets TO 'pericog_admin'@'%'",

        "CREATE TABLE ThisMinute.event_tweets_new LIKE ThisMinute.event_tweets",
        "GRANT ALTER, CREATE, DROP ON ThisMinute.event_tweets_new TO 'pericog_admin'@'%'",
        "GRANT INSERT ON ThisMinute.event_tweets_new TO 'pericog_limited'@'%'",

        "CREATE TABLE ThisMinute.event_tweets_old LIKE ThisMinute.event_tweets",
        "GRANT CREATE, DROP, INSERT ON ThisMinute.event_tweets_old TO 'pericog_admin'@'%'",
    ];

$error = false;
$db = new mysqli($config['connections'][$db_name], "root", $root_password);
foreach ($queries as $query)
{
    $result = var_export($db->query($query), true);
    echo "$query : \n RESULT: $result\n\n";
    if ($result == 'false')
        $error = true;
}

if ($error)
    echo "\n\n*** SOME QUERIES FAILED, PLEASE REVIEW THE LOG ***\n\n\n";
