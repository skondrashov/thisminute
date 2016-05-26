<?php
$db = new mysqli("localhost", "press", file_get_contents('/srv/auth/press.pw'));
$config = parse_ini_file("/srv/etc/config/daemons.ini", true);

$result = $db->query("SELECT * FROM NYC.events");

if ($result)
	echo json_encode($result->fetch_all(MYSQLI_ASSOC));
$result->close();
$db->close();