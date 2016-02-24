<?php
$db = new mysqli("localhost", "press", file_get_contents('/srv/etc/auth/press.pw'));
$where = "WHERE 1=1";
if (isset($_GET['start']))
{
	$where = " AND start_time >= {$_GET['start_time']}";
	if (isset($_GET['end']))
	{
		$where .= " AND end_time <= {$_GET['end_time']}";
	}
}

$result = $db->query("SELECT word, start_time AS time FROM NYC.superevents $where ORDER BY start_time DESC;");
if ($result)
	echo json_encode($result->fetch_all(MYSQLI_ASSOC));
$result->close();
$db->close();