<?php
$db = new mysqli("localhost", "press", file_get_contents('/srv/auth/press.pw'), "ThisMinute");
$config = parse_ini_file("/srv/etc/config/daemons.ini", true);

$result = [];
if (!($query = $db->query("SELECT * FROM events;")))
	echo "error1";
$result["events"] = $query->fetch_all(MYSQLI_ASSOC);
$query->close();

if (!($query = $db->query("SELECT * FROM event_tweets ORDER BY time ASC LIMIT 10;")))
	echo "error2";
$result["tweets"] = $query->fetch_all(MYSQLI_ASSOC);
$query->close();

echo json_encode($result);
$db->close();