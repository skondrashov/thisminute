<?php declare(strict_types=1);

$config = parse_ini_file("/srv/config.ini", true);
$db = pg_connect(
		'host=' . $config['connections'][$config['connections']['active']] . ' ' .
		'user=sentinel ' .
		'password=' . file_get_contents('/srv/auth/sql/sentinel.pw') . ' ' .
		'dbname=thisminute'
	);

echo json_encode([
		"events" => pg_fetch_all(pg_query($db, 'SELECT * FROM events;')) ?: [],
		"tweets" => pg_fetch_all(pg_query($db, '
				SELECT
					*,
					ST_X(geo::geometry) AS lon,
					ST_Y(geo::geometry) AS lat
				FROM tweet_events
				JOIN tweets ON id=tweet_id
				ORDER BY time DESC
				LIMIT 50;
			')) ?: [],
	]);
