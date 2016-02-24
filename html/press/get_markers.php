<?php
$db = new mysqli("localhost", "press", file_get_contents('/srv/etc/auth/press.pw'), "events");

$table = $_GET['word'] . '_' . $_GET['place'] . '_' . $_GET['time'];

$result = $db->query("SELECT * FROM $table ORDER BY time;");
if ($result)
	echo json_encode($result->fetch_all(MYSQLI_ASSOC));
$result->close();
$db->close();
