#!/usr/bin/env php
<?php

$config = parse_ini_file("/srv/config.ini", true);
$db_name = $config['connections']['active'];

$root_password            = $argv[1];
$sentinel_password        = file_get_contents("/srv/auth/daemons/sentinel.pw");
$archivist_password       = file_get_contents("/srv/auth/daemons/archivist.pw");
$pericog_limited_password = file_get_contents("/srv/auth/daemons/pericog_limited.pw");
$pericog_admin_password   = file_get_contents("/srv/auth/daemons/pericog_admin.pw");
$tweet2vec_password       = file_get_contents("/srv/auth/daemons/tweet2vec.pw");

$tweet2vec_vector = [];
foreach (range(0, $config['tweet2vec']['vector_size'] - 1) as $i)
{
	$tweet2vec_vector[] = "v{$i} DOUBLE DEFAULT NULL";
}
$tweet2vec_vector = implode(',', $tweet2vec_vector);

$queries = [
		"DROP USER IF EXISTS
			'sentinel'@'%',
			'archivist'@'%',
			'tweet2vec'@'%',
			'pericog_limited'@'%',
			'pericog_admin'@'%'
			",

		"CREATE USER
			'sentinel'@'%'        IDENTIFIED BY '{$sentinel_password}',
			'archivist'@'%'       IDENTIFIED BY '{$archivist_password}',
			'tweet2vec'@'%'       IDENTIFIED BY '{$tweet2vec_password}',
			'pericog_limited'@'%' IDENTIFIED BY '{$pericog_limited_password}',
			'pericog_admin'@'%'   IDENTIFIED BY '{$pericog_admin_password}'
			",

		"CREATE DATABASE ThisMinute",

		/******************************************
		* DO NOT EVER:                            *
		* - DROP DATABASE ThisMinute              *
		* - DROP TABLE ThisMinute.tweets          *
		* - DROP TABLE ThisMinute.training_tweets *
		******************************************/
		"DROP TABLE IF EXISTS
			ThisMinute.tweet_vectors,
			ThisMinute.events,
			ThisMinute.events_new,
			ThisMinute.events_old,
			ThisMinute.event_tweets,
			ThisMinute.event_tweets_new,
			ThisMinute.event_tweets_old
			",

		"CREATE TABLE ThisMinute.tweets (
				id    BIGINT   NOT NULL AUTO_INCREMENT,
				time  DATETIME NOT NULL DEFAULT NOW(),
				lon   DOUBLE   NOT NULL,
				lat   DOUBLE   NOT NULL,
				exact BOOLEAN  NOT NULL,
				user  BIGINT   NOT NULL,
				text  TEXT     NOT NULL,
				INDEX (time),
				PRIMARY KEY (id)
			)",

		"GRANT INSERT ON ThisMinute.tweets TO 'archivist'@'%'",
		"GRANT SELECT ON ThisMinute.tweets TO 'tweet2vec'@'%'",
		"GRANT SELECT ON ThisMinute.tweets TO 'pericog_admin'@'%'",

		"CREATE TABLE ThisMinute.training_tweets (
				tweet_id BIGINT NOT NULL,
				time  DATETIME  NOT NULL,
				lon   DOUBLE    NOT NULL,
				lat   DOUBLE    NOT NULL,
				text  TEXT      NOT NULL,
				FOREIGN KEY (tweet_id)
					REFERENCES ThisMinute.tweets (id)
					ON DELETE CASCADE
			)",

		"GRANT DELETE, INSERT, SELECT ON ThisMinute.training_tweets TO 'tweet2vec'@'%'",

		"CREATE TABLE ThisMinute.tweet_vectors (
				tweet_id BIGINT  NOT NULL,
				status   TINYINT NOT NULL DEFAULT 0,
				{$tweet2vec_vector},
				FOREIGN KEY (tweet_id)
					REFERENCES ThisMinute.tweets (id)
					ON DELETE CASCADE
			)",

		"GRANT DELETE, SELECT, UPDATE ON ThisMinute.tweet_vectors TO 'tweet2vec'@'%'",
		"GRANT INSERT, SELECT, UPDATE ON ThisMinute.tweet_vectors TO 'pericog_admin'@'%'",

		"CREATE TABLE ThisMinute.events (
				id         BIGINT   NOT NULL,
				lon        DOUBLE   NOT NULL,
				lat        DOUBLE   NOT NULL,
				start_time DATETIME NOT NULL,
				end_time   DATETIME NOT NULL,
				users      INT      NOT NULL,
				PRIMARY KEY (id)
			)",
		"GRANT SELECT ON ThisMinute.events TO 'sentinel'@'%'",
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
		"GRANT SELECT ON ThisMinute.event_tweets TO 'sentinel'@'%'",
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
	$query = str_replace("\t", ' ', $query);
	$result = var_export($db->query($query), true);
	echo "$query : \n RESULT: ";
	if ($result == 'false')
	{
		$error = true;
		echo "Error: " . $db->error;
	}
	else
	{
		echo "Success";
	}
	echo "\n\n";
}

if ($error)
	echo "\n\n*** SOME QUERIES FAILED, PLEASE REVIEW THE LOG FOR ERRORS ***\n\n\n";
