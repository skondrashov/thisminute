<?php declare(strict_types=1);

if (!(
	in_array($_SERVER['REMOTE_ADDR'], [
			'76.206.40.123',
		]) &&
	isset($_POST['id']) &&
	isset($_POST['vote'])
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

pg_query_params($db, '
		INSERT INTO tweet_votes
			(tweet_id, address, value)
		VALUES
			($1, $2, $3);
	', [
		$_POST['id'],
		$_SERVER['REMOTE_ADDR'],
		$_POST['vote'],
	]);

echo 'success';
