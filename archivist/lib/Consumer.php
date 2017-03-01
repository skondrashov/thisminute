<?php
class Consumer extends OauthPhirehose
{
	private $target;

	public function __construct($username, $password, $method = Phirehose::METHOD_SAMPLE, $format = self::FORMAT_JSON, $lang = FALSE)
	{
		parent::__construct($username, $password, $method, $format, $lang);
		$config = parse_ini_file("/srv/config.ini", true);
		$this->target = $config['connections'][$config['connections']['active']];
	}

	// This function is called automatically by the Phirehose class
	// when a new tweet is received with the JSON data in $status
	public function enqueueStatus($status)
	{
		static $db;
		if (!isset($db))
		{
			$db = new mysqli(
				$this->target,
				"archivist",
				file_get_contents("/srv/auth/mysql/archivist.pw"),
				"ThisMinute");
		}

		$stream_item = json_decode($status);
		if (!(isset($stream_item->id_str))) {return;}
		$text = preg_replace('/\s+/', ' ', trim($stream_item->text));

		// calculate location information to write to database
		// if GPS location is given, use that
		// if not, then calculate the middle of the given bounding box for the set location (eg Brooklyn, NY)
		// if both are given, then GPS location will be used, which can result in tweets outside of our search location
		// for now, this is okay, because tweets about home from people away from home may still be valuable
		if ($stream_item->coordinates)
		{
			$lon = $stream_item->coordinates->coordinates[0];
			$lat = $stream_item->coordinates->coordinates[1];
			$exact = 1;
		}
		else
		{
			$box_vertices = $stream_item->place->bounding_box->coordinates;
			$lon = $lat = 0.0;
			foreach ($box_vertices[0] as $point)
			{
				$lon += floatval($point[0]);
				$lat += floatval($point[1]);
			}
			$lon /= count($box_vertices[0]);
			$lat /= count($box_vertices[0]);
			$exact = 0;
		}

		$db->query("INSERT INTO tweets (lon, lat, exact, user, text)
			VALUES ($lon, $lat, $exact, {$stream_item->user->id_str}, '$text');");
	}

	public function log($message, $level = 'notice')
	{
		print $message;
	}
}
