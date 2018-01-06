<?php declare(strict_types=1);

$config = parse_ini_file("/srv/config.ini", true);
$db = pg_connect(
		'host=' . $config['connections'][$config['connections']['active']] . ' ' .
		'user=sentinel ' .
		'password=' . file_get_contents('/srv/auth/sql/sentinel.pw') . ' ' .
		'dbname=thisminute'
	);

$limit = $_GET['n'] ?? 1;
$limit = max(min(100, (int)$limit), 1);

$result = pg_query_params($db, 'SELECT text FROM tweets ORDER BY TIME DESC LIMIT $1;', [$limit]);

if (!$result) {
	die();
}

$texts = [];
foreach (pg_fetch_all($result) as $row) {
	$texts []= $row['text'];
}

if (!empty($_GET['format'])) {
	echo implode("<br>", $texts);
} else {
	echo json_encode($texts);
}
