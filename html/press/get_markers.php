<?php
$db = new mysqli("localhost", "press", file_get_contents('/srv/etc/auth/press.pw'));
$config = parse_ini_file("/srv/etc/config/daemons.ini", true);

$result = $db->query("SELECT * FROM NYC.event_tweets WHERE event_id IN (SELECT * FROM (SELECT id FROM NYC.superevents WHERE end_time < FROM_UNIXTIME(UNIX_TIMESTAMP() - " . $config['display']['lookahead'] .
	") ORDER BY start_time DESC LIMIT 5) temp_tab) ORDER BY time DESC;");

if ($result)
	echo json_encode($result->fetch_all(MYSQLI_ASSOC));
$result->close();
$db->close();