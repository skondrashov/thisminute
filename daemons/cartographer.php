#!/usr/bin/env php
<?php

$db = new mysqli("localhost", "cartographer", "LKWDZQnFQvhgQPg3", "events");

$db->query("UPDATE NYC.events SET mapped=1 WHERE mapped=0 OR mapped=3;");
$events = $db->query("SELECT time, word FROM NYC.events WHERE mapped=1;");

$success = true;


while ($event = $events->fetch_assoc())
{
	$word  = $event['word'];
	$time  = strtotime($event['time']);

	$start = date('Y-m-d H:i:s', $time - 3600);
	$end   = date('Y-m-d H:i:s', $time + 3600);
	$table = "{$word}_NYC_{$time}";

	if (!$db->query("SHOW TABLES LIKE '$table';")->num_rows)
	{
		$db->query("CREATE TABLE $table LIKE NYC.tweets;");
		$db->query("ALTER TABLE $table ADD PRIMARY KEY (time, lat, lon);");
	}
	$db->query("INSERT IGNORE INTO $table SELECT * FROM NYC.tweets WHERE " .
		"time BETWEEN '$start' AND '$end' " .
		"AND MATCH(text) AGAINST ('" . $event['word'] . "');");

	if ($time + 3600 < time())
	{
		$db->query("UPDATE NYC.events SET mapped=2 WHERE word='$word';");
	}
}
