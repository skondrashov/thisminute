<?php
$db = new mysqli("localhost", "press", "U9dB5VWD3qpGvDKb", "NYC");

if ($db->connect_error) {
	echo "ERROR LOL";
}

$events = $db->query('SELECT * FROM events WHERE mapped=2 ORDER BY time;')->fetch_all(MYSQLI_ASSOC);

?>
<!doctype HTML>
<html>
	<head>
		<title>NYC Tweet Mapper</title>
	</head>
	<body>
		<?php
		foreach ($events as $event)
		{
			echo '<a href="map.php?word=' . $event['word'] . '&time=' . strtotime($event['time']) . '">' . $event['word'] . '</a><br>';
		}
		?>
	</body>
</html>
