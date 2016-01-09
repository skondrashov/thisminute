<?php
require 'lib/stats.php';
require 'stats/settings.php';

define('COUNT_THRESHOLD', 1);

$db = new mysqli("localhost", "statistician", "mightmakesright", "NYC");
if ($db->connect_error)
{
	die("Connection failed: " . $db->connect_error);
}

// define the latest tweet time, move backwards from that point for calculations
$interval_start = strtotime($db->query('SELECT Max(time) FROM tweets;')->fetch_row()[0]);

// define an ending point for the calculations - either the beginning of records, or a predefined recall scope, whichever gives fewer results
$beginning_of_time = strtotime($db->query('SELECT Min(time) FROM tweets;')->fetch_row()[0]);
if ($beginning_of_time < $interval_start - RECALL_SCOPE)
{
	$beginning_of_time = $interval_start - RECALL_SCOPE;
}
else
{
	echo "Not enough data to look back " . RECALL_SCOPE . " seconds, starting from beginning of records instead. (" . ($interval_start-$beginning_of_time) . " seconds ago)\n";
}

$word_counts = [];

for ($i = 0;
	$interval_start >= ($beginning_of_time + TIME_GRANULARITY);
	($i++) & ($interval_start -= TIME_GRANULARITY)
)
{
	$query = "SELECT user, text FROM tweets WHERE time <= FROM_UNIXTIME($interval_start) and time > FROM_UNIXTIME(" . ($interval_start - TIME_GRANULARITY) . ');';
	$new_tweets = $db->query($query)->fetch_all();

	foreach (countWords($new_tweets, COUNT_THRESHOLD) as $word => $value)
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

	// ignore words that appear less often than (about) once an hour
	if ($mean / TIME_GRANULARITY > 0.0003)
	{
		$query .= "(\"$word\",$mean,$deviation),";
	}
}

$query = substr_replace($query, ' ON DUPLICATE KEY UPDATE expected_value=VALUES(expected_value), standard_deviation=VALUES(standard_deviation);', -1);

$db->query($query);
