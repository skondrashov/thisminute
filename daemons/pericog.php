#!/usr/bin/env php
<?php
require 'lib/stats.php';

$last_runtime = time() - EVENT_CHECK_PERIOD;
$db = new mysqli("localhost", "pericog", "Mg9tajcdNSUdpsVq", "NYC");
if ($db->connect_error)
{
	die("Connection failed: " . $db->connect_error);
}

while (1)
{
	if (time() - $last_runtime > EVENT_CHECK_PERIOD)
	{
		$new_tweets = $db->query('SELECT user, text FROM tweets WHERE time > FROM_UNIXTIME(' . ($last_runtime - TIME_GRANULARITY) . ')')->fetch_all();
		$word_stats = $db->query('SELECT * FROM stats;')->fetch_all();

		$word_stats_assoc = [];
		foreach ($word_stats as $word_stat)
		{
			$word_thresholds[$word_stat[0]] = floatval($word_stat[1]) + floatval($word_stat[2]) * 10;
		}

		$word_counts = countWords($new_tweets);
		$last_runtime = time();

		foreach ($word_counts as $word => $count)
		{
			$detected = false;
			if (isset($word_thresholds[$word]))
			{
				if ($count > $word_thresholds[$word])
				{
					$detected = true;
				}
			}
			elseif ($count > 10)
			{
				$detected = true;
			}

			if ($detected)
			{
				$previous = $db->query("SELECT time FROM events WHERE word='$word' ORDER BY time LIMIT 1;")->num_rows;
				if (!$previous)
				{
					$db->query("INSERT INTO events (word) VALUES ('$word');");
				}
			}
		}
	}
}
