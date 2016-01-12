<?php
require 'stats/settings.php';

function countWords($tweets)
{
	$unique_words = [];

	// combine all tweets from a single user for the purposes of word counting
	foreach ($tweets as $tweet)
	{
		if (!isset($unique_words[$tweet[0]]))
		{
			$unique_words[$tweet[0]] = '';
		}

		$unique_words[$tweet[0]] .= ' ' . $tweet[1];
	}

	foreach ($unique_words as &$words)
	{
		$words = strtolower($words);

		// remove mentions and URLs
		$words = preg_replace('/((\B@)|(\bhttps?:\/\/))[^\s]+/', '', $words);

		// treat all non-word characters as spaces
		$words = preg_replace("/[^\w]+/", ' ', $words);
		$words = trim($words);
		$words = explode(' ', $words);

		// remove duplicates
		$words = array_unique($words);
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

	// sometimes an empty character is recorded
	unset($word_counts['']);

	// the & character is generated as the word "amp" right now... squelch for now
	unset($word_counts['amp']);

	return $word_counts;
}