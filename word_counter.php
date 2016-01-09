<?php
require 'lib/stats.php';
require 'stats/settings.php';

define('COUNT_THRESHOLD', 1);

$last_runtime = time() - TIME_GRANULARITY;
$db = new mysqli("localhost", "responder", "lovepotion", "NYC");
if ($db->connect_error)
{
    die("Connection failed: " . $conn->connect_error);
}

while (1)
{
	if (time() - $last_runtime > TIME_GRANULARITY)
	{
		$new_tweets = $db->query('SELECT user, text FROM tweets WHERE time > FROM_UNIXTIME(' . ($last_runtime - TIME_GRANULARITY) . ')')->fetch_all();

		$word_counts = countWords($new_tweets, COUNT_THRESHOLD);
		$last_runtime = time();
		$table_name = 'time' . $last_runtime;

		$db->query("CREATE TABLE $table_name (word text NOT NULL, count int NOT NULL);");

		$query = "INSERT INTO $table_name (word, count) VALUES ";
		foreach ($word_counts as $word => $count)
		{
			$query .= "(\"$word\",$count),";
		}
		$query = substr_replace($query, ';', -1);

		$db->query($query);
	}
}
