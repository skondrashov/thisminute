<?php declare(strict_types=1);

define('CONFIG', parse_ini_file("/srv/config.ini", true));
define('DB', pg_connect(
		'host=' . CONFIG['connections'][CONFIG['connections']['active']] . ' ' .
		'user=sentinel ' .
		'password=' . file_get_contents('/srv/auth/sql/sentinel.pw') . ' ' .
		'dbname=thisminute'
	));

function fetch($query, $params=[])
{
	return pg_fetch_all(pg_query_params(DB, $query, $params)) ?: [];
}

$events = fetch('SELECT * FROM events');
$count = fetch('
		SELECT
			0 AS count
		FROM tweets
		LIMIT 1
	');

switch (CONFIG['display']['source']) {
	case 'crowdflower':
		$tweets = fetch('
				SELECT
					*,
					ST_X(geo::geometry) AS lon,
					ST_Y(geo::geometry) AS lat
				FROM tweets
				WHERE id IN (
					SELECT tv.tweet_id
					FROM tweet_votes tv
					LEFT JOIN tweet_votes tv2 ON
						tv2.tweet_id = tv.tweet_id AND
						tv2.user_ip = $1
					WHERE
						tv.user_ip = \'1.1.1.1\' AND (
							tv2.submit IS NULL OR
							tv2.submit = FALSE
						)
				)
				ORDER BY id DESC
				LIMIT 20
			', [
				$_SERVER['REMOTE_ADDR'],
			]);
		$count = fetch('
				SELECT COUNT(*) AS count
				FROM tweet_votes tv
				LEFT JOIN tweet_votes tv2 ON
					tv2.tweet_id = tv.tweet_id AND
					tv2.user_ip = $1
				WHERE
					tv.user_ip = \'1.1.1.1\' AND (
						tv2.submit IS NULL OR
						tv2.submit = FALSE
					)
			', [
				$_SERVER['REMOTE_ADDR'],
			]);
		break;
	case 'all':
		$tweets = fetch('
				SELECT
					*,
					ST_X(geo::geometry) AS lon,
					ST_Y(geo::geometry) AS lat
				FROM tweets
				ORDER BY id DESC
				LIMIT 50
			');
		break;
	case 'breaking':
		$tweets = fetch('
				SELECT
					*,
					ST_X(geo::geometry) AS lon,
					ST_Y(geo::geometry) AS lat
				FROM tweets
				JOIN tweet_votes ON
					id=tweet_id
				WHERE
					user_ip = \'0.0.0.0\' AND
					disaster = TRUE
				ORDER BY id DESC
				LIMIT 20
			');
		break;
}

echo json_encode([
		"events" => $events,
		"tweets" => $tweets,
		"count"  => $count,
	]);

