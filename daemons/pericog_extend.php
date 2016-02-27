#!/usr/bin/env php
<?php

$last_runtime = 1456460400 - 60*60*24*2;

while ($last_runtime < 1456460400 + 60*60*24*2)
{
	echo "$last_runtime ------------------\n";
	$out = [];
	exec("/srv/bin/pericog -l " . $last_runtime . " -H" . (($last_runtime > 1456460400) ? " -o" : ""), $out);
	foreach ($out as $thing)
	{
		echo "$thing\n";
	}
	$last_runtime += 600;
}
