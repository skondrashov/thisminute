<?php
$db = new mysqli("localhost", "press", "U9dB5VWD3qpGvDKb", "NYC");

if ($db->connect_error) {
    die("Connection failed: " . $db->connect_error);
}

$result = $db->query('SELECT * FROM events WHERE mapped != 0 ORDER BY time;');
if ($result)
	echo json_encode($result->fetch_all());
$result->close();
$db->close();
