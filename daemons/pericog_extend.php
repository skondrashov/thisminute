#!/usr/bin/env php
<?php
$config = parse_ini_file("/srv/etc/config/daemons.ini", true);

$filename =	"/root/test/" .
	$config['threshold']['spacial_percentage'] . "_" .
	$config['threshold']['temporal_percentage'] . "_" .
	$config['threshold']['spacial_deviations'] . "_" .
	$config['threshold']['temporal_deviations'] . ".txt";

$last_runtime = 1456617600;

while ($last_runtime < 1456941093)
{
	echo "$last_runtime ------------------\n";
	$out = [];
	exec("/srv/bin/pericog -l $last_runtime" . (($last_runtime > 1456617600 + 60*60*48) ? " -o -v $filename" : ""), $out);
	foreach ($out as $thing)
	{
		echo "$thing\n";
	}
	$last_runtime += 600;
}
