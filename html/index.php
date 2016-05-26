<!doctype HTML>
<html>
	<head>
		<title>NYC Tweet Mapper</title>
		<meta charset="utf-8">
		<style type="text/css">
			html, body { height: 100%; margin: 0; padding: 0; }
			#header { height: 60px; background-color: #000; color: #FFF; margin-left: auto; text-align: center; font: 50px arial, sans-serif; }
			#box { width: 100%; position: absolute; top: 60px; bottom: 0; overflow:hidden;}
			#map { height: 100%; width: 1500px; float: left; }
			.infobox { overflow: hidden; padding: 10px; font: 14px arial, sans-serif; }
		</style>
	</head>
	<body>
		<script src="lib/poll.js"></script>
		<div id="header">ThisMinute</div>
		<div id="box">
			<div id="map"></div>
			<div id="sidebar">butt</div>
		</div>
		<script async defer
			src="https://maps.googleapis.com/maps/api/js?key=AIzaSyCLWGtBTbTki6xwphWDWOPfZ4Csl2CtqlI&callback=initMap">
		</script>
	</body>
</html>
