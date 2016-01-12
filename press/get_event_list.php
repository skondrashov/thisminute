<?php
$db = new mysqli("localhost", "press", "U9dB5VWD3qpGvDKb", "NYC");

if ($db->connect_error) {
    die("Connection failed: " . $db->connect_error);
}

$result = $db->query('SELECT * FROM events ORDER BY time WHERE mapped=2;');
echo json_encode($result->fetch_all());
$result->close();
$db->close();
