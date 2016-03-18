<?php
$config = parse_ini_file("/srv/etc/config/daemons.ini", true);

$last_runtime = file_get_contents("/etc/ochre/runtimes/" . DAEMON);
if (!$last_runtime)
{
	$last_runtime = time() - $config['timing']['period'];
}

$db = new mysqli("localhost", DAEMON, file_get_contents("/srv/etc/auth/daemons/" . DAEMON . ".pw"));
if ($db->connect_error)
{
	error_log("Database connection failed for " . DAEMON . " daemon: " . $db->connect_error);
}

while (1)
{
	if (time() - $last_runtime > $config['timing']['period'])
	{
		daemon($db, $last_runtime, $config);
		file_put_contents("/etc/ochre/runtimes/" . DAEMON, $last_runtime);
		$last_runtime += $config['timing']['period'];
	}
	sleep(1);
}
