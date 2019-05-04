<?php declare(strict_types=1);

if (!(
	in_array($_SERVER['REMOTE_ADDR'], [
			'76.206.40.123',
			'24.128.191.208',
			'104.191.244.200',
			'68.32.143.90',
		]) &&
	isset($_POST['id'])
))
{
	die();
}

$config = parse_ini_file("/srv/config.ini", true);
$db = pg_connect(
		'host=' . $config['connections'][$config['connections']['active']] . ' ' .
		'user=sentinel ' .
		'password=' . file_get_contents('/srv/auth/sql/sentinel.pw') . ' ' .
		'dbname=thisminute'
	);

$_POST['tweet_id'] = $_POST['id'];
$_POST['user_ip'] = $_SERVER['REMOTE_ADDR'];

$columns = $values = $updates = $params = [];
$i = 1;
foreach ([
	'tweet_id',
	'user_ip',
	'spam',
	'fiction',
	'poetry',
	'use',
	'event',
	'disaster',
	'personal',
	'eyewitness',
	'secondhand',
	'breaking',
	'informative',
	'submit',
] as $property) {
	if (array_key_exists($property, $_POST)) {
		array_push($columns, $property);
		array_push($values,  "\${$i}");
		array_push($updates, "{$property}=\${$i}");
		array_push($params,  $_POST[$property]);
		$i++;
	}
}

$columns = implode(',', $columns);
$values  = implode(',', $values);
$updates = implode(',', $updates);

pg_query_params($db, "
		INSERT INTO tweet_votes ({$columns})
		VALUES ({$values})
		ON CONFLICT (tweet_id, user_ip)
		DO UPDATE
		SET {$updates}
	", $params);

if (isset($_POST['disaster'])) {
	pg_query_params($db, "
			INSERT INTO tweet_properties (tweet_id, crowdflower, random_forest_train)
			VALUES ($1, $2, TRUE)
			ON CONFLICT (tweet_id)
			DO UPDATE
			SET random_forest_train=TRUE
		", [
			$_POST['tweet_id'],
			$_POST['disaster'],
		]);
}

echo 'success';
