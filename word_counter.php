<?php
define('TIME_GRANULARITY', 3600);
define('COUNT_THRESHOLD', 0);

$last_runtime = time() - TIME_GRANULARITY;
$db = new mysqli("localhost", "tweets_user", "lovepotion", "NYC");
if ($db->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

while (1)
{
	if (time() - $last_runtime > TIME_GRANULARITY)
	{
		$new_tweets = $db->query('SELECT user, text FROM tweets WHERE time > FROM_UNIXTIME(' . ($last_runtime - TIME_GRANULARITY) . ')')->fetch_all();
		$unique_words = [];

		// combine all tweets from a single user for the purposes of word counting
		foreach ($new_tweets as $tweet)
		{
			if (!isset($unique_words[$tweet[0]]))
			{
				$unique_words[$tweet[0]] = '';	
			}

			$unique_words[$tweet[0]] .= ' ' . $tweet[1];	
		}

		foreach ($unique_words as &$words)
		{
			// remove mentions and URLs
			$words = trim(preg_replace('/((\B@)|(\bhttps?:\/\/))[^\s]+/', '', strtolower($words)));

			// explode by non-words
			$words = array_unique(preg_split("/[^\w]+/", $words));
		}

		$word_counts = [];
		foreach ($unique_words as $words)
		{
			foreach ($words as $word)
			{
				if (!isset($word_counts[$word]))
				{
					$word_counts[$word] = 1;
				}
				else
				{
					$word_counts[$word]++;
				}
			}
		}

		// sometimes a null character is generated as a word - just squelch it
		unset($word_counts['']);

		$last_runtime = time();
		$table_name = 'time' . $last_runtime;

		$db->query("CREATE TABLE $table_name (word text NOT NULL, count int NOT NULL);");

		$query = "INSERT INTO $table_name (word, count) VALUES ";
		foreach ($word_counts as $word => $count)
		{
			if ($count > COUNT_THRESHOLD)
			{
				$query .= "(\"$word\",$count),";
			}
		}
		$query = substr_replace($query, ';', -1);

		$db->query($query);
	}
}


$result->close();
$db->close();

