#!/usr/bin/env php
<?php
$root_password            = file_get_contents("/srv/auth/root.pw");
$archivist_password       = file_get_contents("/srv/auth/daemons/archivist.pw");
$pericog_admin_password   = file_get_contents("/srv/auth/daemons/pericog_admin.pw");
$pericog_limited_password = file_get_contents("/srv/auth/daemons/pericog_limited.pw");

$db = new mysqli("localhost", "root", $root_password);
$queries = [
        "CREATE DATABASE ThisMinute",
        "CREATE USER 'archivist'@'localhost'       IDENTIFIED BY '{$archivist_password}'",
        "CREATE USER 'pericog_admin'@'localhost'   IDENTIFIED BY '{$pericog_admin_password}'",
        "CREATE USER 'pericog_limited'@'localhost' IDENTIFIED BY '{$pericog_limited_password}'",
        "CREATE TABLE ThisMinute.tweets (
                lon   DOUBLE    NOT NULL,
                lat   DOUBLE    NOT NULL,
                exact BOOLEAN   NOT NULL,
                text  TEXT      NOT NULL,
                user  BIGINT    NOT NULL,
                time  TIMESTAMP NOT NULL DEFAULT NOW()
            )",
        "GRANT INSERT ON ThisMinute.tweets TO 'archivist'@'localhost'",
    ];
foreach ($queries as $query)
    $db->query($query);
