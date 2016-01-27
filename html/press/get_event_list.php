<?php
$db = new mysqli("localhost", "press", file_get_contents('/srv/auth/press.pw'), "NYC");

$where = 'WHERE mapped!=0 ';

if (isset($_GET['start']))
{
	$where .= " AND time >= {$_GET['start_time']}";
	if (isset($_GET['end']))
	{
		$where .= " AND time <= {$_GET['end_time']}";
	}
}

$result = $db->query("SELECT * FROM events $where ORDER BY time DESC;");
if ($result)
	echo json_encode($result->fetch_all(MYSQLI_ASSOC));
$result->close();
$db->close();
