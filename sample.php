<?php
define ("MAX_MARKERS", 15);

$db = new mysqli("localhost", "tweets_user", "lovepotion", "tweets");

if ($db->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

$result = $db->query('SELECT * FROM NYC_exact ORDER BY time DESC LIMIT ' . MAX_MARKERS);
echo json_encode($result->fetch_all());
$result->close();
$db->close();


