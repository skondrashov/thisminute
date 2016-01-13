#!/usr/bin/env php
<?php
require 'lib/stats.php';

$last_runtime = time() - CARTOGRAPHER_PERIOD;
$db = new mysqli("localhost", "cartographer", "LKWDZQnFQvhgQPg3", "events");
if ($db->connect_error)
{
	die("Connection failed: " . $db->connect_error);
}

while (1)
{
	if (time() - $last_runtime > CARTOGRAPHER_PERIOD)
	{
		$db->query("UPDATE NYC.events SET mapped=1 WHERE mapped=0 OR mapped=3;");
		$events = $db->query("SELECT time, word FROM NYC.events WHERE mapped=1;");

		while ($event = $events->fetch_assoc())
		{
			$word  = $event['word'];
			$time  = strtotime($event['time']);

			$start = date('Y-m-d H:i:s', $time - CARTOGRAPHER_LOOKBACK);
			$end   = date('Y-m-d H:i:s', $time + CARTOGRAPHER_LOOKAHEAD);
			$table = "{$word}_NYC_{$time}";

			if (!$db->query("SHOW TABLES LIKE '$table';")->num_rows)
			{
				$db->query("CREATE TABLE $table LIKE NYC.tweets;");
				$db->query("ALTER TABLE $table ADD PRIMARY KEY (time, lat, lon);");
			}
			$db->query("INSERT IGNORE INTO $table SELECT * FROM NYC.tweets WHERE " .
				"time BETWEEN '$start' AND '$end' " .
				"AND MATCH(text) AGAINST ('" . $event['word'] . "');");

			if ($time + CARTOGRAPHER_LOOKAHEAD < time())
			{
				$db->query("UPDATE NYC.events SET mapped=2 WHERE word='$word';");
			}
		}
		$last_runtime = time();
	}
}
