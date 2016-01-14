#!/usr/bin/env php
<?php
require 'lib/stats.php';

$last_runtime = time() - STATISTICIAN_PERIOD;
$db = new mysqli("localhost", "statistician", file_get_contents("/srv/auth/daemons/statistician.pw"), "NYC");
if ($db->connect_error)
{
	die("Connection failed: " . $db->connect_error);
}

while (1)
{
	if (time() - $last_runtime > STATISTICIAN_PERIOD)
	{
		// define the latest tweet time, move backwards from that point for calculations
		$interval_start = strtotime($db->query('SELECT Max(time) FROM tweets;')->fetch_row()[0]);

		// define an ending point for the calculations - either the beginning of records, or a predefined recall scope, whichever gives fewer results
		$beginning_of_time = strtotime($db->query('SELECT Min(time) FROM tweets;')->fetch_row()[0]);
		if ($beginning_of_time < $interval_start - STATISTICIAN_RECALL_SCOPE)
		{
			$beginning_of_time = $interval_start - STATISTICIAN_RECALL_SCOPE;
		}
		else
		{
			echo "Not enough data to look back " . STATISTICIAN_RECALL_SCOPE . " seconds, starting from beginning of records instead.\n";
		}

		echo "Gathering data between " . date("o-m-d H:i:s", $beginning_of_time) . " (" . ($interval_start-$beginning_of_time) . " seconds ago) and now (" . date("o-m-d H:i:s", $interval_start) . ").\n";

		$word_counts = [];

		for ($i = 0;
			$interval_start >= ($beginning_of_time + TIME_GRANULARITY);
			($i++) & ($interval_start -= TIME_GRANULARITY)
		)
		{
			$query = "SELECT user, text FROM tweets WHERE time <= FROM_UNIXTIME($interval_start) and time > FROM_UNIXTIME(" . ($interval_start - TIME_GRANULARITY) . ');';
			$new_tweets = $db->query($query)->fetch_all();

			foreach (countWords($new_tweets) as $word => $value)
			{
				$word_counts[$word][] = $value;
			}
		}

		$query = "INSERT INTO stats (word, expected_value, standard_deviation) VALUES ";

		// calculate expected value and standard deviation for each word
		foreach ($word_counts as $word => $value_array)
		{
			$mean = array_sum($value_array)/$i;

			$num_zeroes = $i - count($value_array);

			$variance = $num_zeroes * pow(0 - $mean, 2);
			foreach ($value_array as $count)
			{
				$variance += pow($count - $mean, 2);
			}
			$variance /= $i;
			$deviation = sqrt($variance);

			// ignore words that appear less often than once an hour
			if ($mean > TIME_GRANULARITY/(60*60))
			{
				$query .= "(\"$word\",$mean,$deviation),";
			}
		}

		$query = substr_replace($query, ';', -1);

		$db->query("LOCK TABLES stats READ;");
		$db->query("TRUNCATE TABLE stats;");
		$db->query($query);
		$db->query("UNLOCK TABLES;");

		$last_runtime = time();
	}
}
