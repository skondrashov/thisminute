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
		if ($stream_item->coordinates)
		{
			$this->db->query('INSERT INTO NYC_exact (lat, lon, text) values ('
				. $stream_item->coordinates->coordinates[1] . ','
				. $stream_item->coordinates->coordinates[0] . ','
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