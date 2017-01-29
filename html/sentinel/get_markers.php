<?php
$config = parse_ini_file("/srv/config.ini", true);
$target = $config['connections'][$config['connections']['active']];
$db = new mysqli($target, "sentinel", file_get_contents('/srv/auth/daemons/sentinel.pw'), "ThisMinute");

$result = [];
if (!($query = $db->query("SELECT * FROM events;")))
	die();
$result["events"] = $query->fetch_all(MYSQLI_ASSOC);
$query->close();

if (!($query = $db->query("SELECT * FROM event_tweets ORDER BY time ASC;")))
	die();
$result["tweets"] = $query->fetch_all(MYSQLI_ASSOC);
$query->close();

echo json_encode($result);
$db->close();
