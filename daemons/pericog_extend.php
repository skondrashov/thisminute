#!/usr/bin/env php
<?php
$config = parse_ini_file("/srv/etc/config/daemons.ini", true);

$sp	= $config['threshold']['spacial_percentage'];
$tp	= $config['threshold']['temporal_percentage'];
$sd	= $config['threshold']['spacial_deviations'];
$td	= $config['threshold']['temporal_deviations'];

$start_time = 1456617600;
$last_runtime = $start_time;

while ($last_runtime < $start_time + 60*60*192)
{
	// for ($sp = .1; $sp < .5; $sp += .05)
	// for ($tp = .1; $tp < .5; $tp += .05)
	// for ($sd = .5; $sd < 5; $sd += .5)
	// for ($td = .5; $td < 5; $td += .5)
	{
		$filename =	"/root/test/{$sp}_{$tp}_{$sd}_{$td}.txt";
		echo "$last_runtime ------------------\n";
		$out = [];
		exec("/srv/bin/pericog -l $last_runtime -c " . (($last_runtime > $start_time + 60*60*48) ? " -o -v $filename -1 $sp -2 $tp -3 $sd -4 $td" : ""), $out);
		foreach ($out as $thing)
		{
			echo "$thing\n";
		}
	}
	$last_runtime += $config['timing']['period'];
}
