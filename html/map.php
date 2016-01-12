<!doctype HTML>
<html>
	<head>
		<title>NYC Tweet Mapper</title>
		<script src="lib/poll.js"></script>
		<style type="text/css">
			html, body { height: 100%; margin: 0; padding: 0; }
			#map { height: 100%; }
		</style>
		<script type="text/javascript">
			<?php
				echo 'var event_word  = "' . $_GET['word'] . '";';
				echo 'var event_time  = "' . $_GET['time'] . '";';
				echo 'var event_place = "NYC";';
			?>
		</script>
	</head>
	<body>
		<div id="map"></div>
		<script async defer
			src="https://maps.googleapis.com/maps/api/js?key=AIzaSyCLWGtBTbTki6xwphWDWOPfZ4Csl2CtqlI&callback=initMap">
		</script>
	</body>
</html>