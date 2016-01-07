<?php
class Consumer extends OauthPhirehose
{
	public $db;

	// This function is called automatically by the Phirehose class
	// when a new tweet is received with the JSON data in $status
	public function enqueueStatus($status)
	{
		$stream_item = json_decode($status);
		if (!(isset($stream_item->id_str))) { return;}
		$text = preg_replace('/\s+/', ' ', trim($stream_item->text));

		// write geolocated and location-set tweets to different tables
		// NOTE: tweets with both parameters set will be written only to the geolocated tweet table (eg 'NYC_exact')
		if ($stream_item->coordinates)
		{
			$this->db->query('INSERT INTO NYC_exact (lon, lat, text) values ('
				. $stream_item->coordinates->coordinates[0] . ','
				. $stream_item->coordinates->coordinates[1] . ','
				. "'" . $text . "'"
				. ');');
		}
		else
		{
			$this->db->query('INSERT INTO NYC_approx (place_name, text) values ('
				. "'" . $stream_item->place->full_name . "'" . ','
				. "'" . $text . "'"
				. ');');
		}
	}

	public function log($message, $level = 'notice')
	{
		print $message;
	}
}