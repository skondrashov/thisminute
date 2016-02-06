<?php
$config = parse_ini_file("/srv/config/daemons.ini", true);

$last_runtime = file_get_contents("/etc/ochre/runtimes/" . DAEMON);
if (!$last_runtime)
{
	$last_runtime = time() - $config['timing']['period'];
}

$db = new mysqli("localhost", DAEMON, file_get_contents("/srv/auth/daemons/" . DAEMON . ".pw"));
if ($db->connect_error)
{
	error_log("Database connection failed for " . DAEMON . " daemon: " . $db->connect_error);
}

while (1)
{
	$time = time();
	if ($time - $last_runtime > $config['timing']['period'])
	{
		daemon($db, $last_runtime, $config);
		file_put_contents("/etc/ochre/runtimes/" . DAEMON, $time);
		$last_runtime = $time;
	}
}
