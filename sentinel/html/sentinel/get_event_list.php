<?php
$config = parse_ini_file("/srv/config.ini", true);
$target = $config['connections'][$config['connections']['active']];
$db = new mysqli($target, "sentinel", file_get_contents('/srv/auth/mysql/sentinel.pw'), "ThisMinute");

$where = "WHERE 1=1";
if (isset($_GET['start']))
{
	$where = " AND start_time >= {$_GET['start_time']}";
	if (isset($_GET['end']))
	{
		$where .= " AND end_time <= {$_GET['end_time']}";
	}
}

$result = $db->query("SELECT word, start_time AS time FROM superevents $where ORDER BY start_time DESC;");
if ($result)
	echo json_encode($result->fetch_all(MYSQLI_ASSOC));
$result->close();
$db->close();
