<?php
$config = parse_ini_file("/srv/config.ini", true);
$target = $config['connections'][$config['connections']['active']];
$db = new mysqli($target, "sentinel", file_get_contents('/srv/auth/mysql/sentinel.pw'), "ThisMinute");

$limit = $_GET['n'] ?: 1;
$limit = max(min(100, (int)$limit), 1);

$result = [];
if (!($query = $db->query("SELECT text FROM tweets ORDER BY TIME DESC LIMIT $limit"))) {
	die();
}
$result = $query->fetch_all(MYSQLI_ASSOC);
$query->close();

$texts = [];
foreach ($result as $row) {
	$texts []= $row['text'];
}

if ($_GET['format']) {
	echo implode("<br>", $texts);
} else {
	echo json_encode($texts);
}
$db->close();
