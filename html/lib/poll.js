var MIN_OPACITY = .3;

var map, markers = {}, info, icons = [], xhttp, default_icon;
var colors = [
	["#F0A3FF", "#000"],
	["#0075DC", "#000"],
	["#993F00", "#FFF"],
	["#4C005C", "#FFF"],
	["#191919", "#FFF"],
	["#005C31", "#FFF"],
	["#2BCE48", "#000"],
	["#FFCC99", "#000"],
	["#808080", "#000"],
	["#94FFB5", "#000"],
	["#8F7C00", "#000"],
	["#9DCC00", "#000"],
	["#C20088", "#000"],
	["#003380", "#FFF"],
	["#FFA405", "#000"],
	["#FFA8BB", "#000"],
	["#426600", "#FFF"],
	["#FF0010", "#000"],
	["#5EF1F2", "#000"],
	["#00998F", "#FFF"],
	["#E0FF66", "#000"],
	["#740AFF", "#FFF"],
	["#990000", "#FFF"],
	["#FFFF80", "#000"],
	["#FFFF00", "#000"],
	["#FF5005", "#000"]
];

function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: {lat: 40.712783, lng: -74.005942},
		zoom: 12
	});
}
function poll() {
	xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {
		if (xhttp.readyState == 4 && xhttp.status == 200) {
			var result = JSON.parse(xhttp.responseText);
			var ids = [];

			for (var i = 0; i < result.length; i++)
			{
				// create unique id for each tweet received to ensure we don't create duplicates
				var id = ids[i] = result[i].event_id + result[i].lon + result[i].lat + result[i].user;

				// only create a new marker if its id has not been filled
				if (!(id in markers))
				{

					markers[id] = new google.maps.Marker({
							position: {lat: parseFloat(result[i].lat), lng: parseFloat(result[i].lon)},
							map: map,
							title: result[i].time,
							icon: default_icon
						});
					markers[id].event_num = result[i].event_id % colors.length;
					markers[id].highlighted = false;
					markers[id].text = result[i].text;

					(function() {
						var content = result[i].text;
						var marker = markers[id];
						marker.addListener('click', function() {
							info.close();
							info.setContent(content);
							info.open(map, marker);
							});
					})();
				}
			}

			// remove markers that exist locally but were not passed from the server
			for (var marker in markers)
			{
				if (markers.hasOwnProperty(marker))
				{
					if (ids.indexOf(marker) === -1)
					{
						markers[marker].setMap(null);
						delete markers[marker];
					}
				}
			}
		}
	};
	xhttp.open("GET", "press/get_markers.php", true);
	xhttp.send();
	setTimeout(poll, 5000);
}

function highlight(id) {
	if (markers[id].highlighted)
		return;
	markers[id].highlighted = true;
	markers[id].setIcon(icons[markers[id].event_num]);
	update();
}

function dim(id) {
	if (!markers[id].highlighted)
		return;
	markers[id].highlighted = false;
	markers[id].setIcon(default_icon);
	update();
}

function update() {
	$("#sidebar").empty();

	for (var marker in markers)
	{
		if (markers[marker].highlighted)
		{
			$("#sidebar").append($('<div class="infobox">' + markers[marker].text + '</div>"'));
			$("#sidebar:last-child").css('background-color', colors[markers[marker].event_num][0]);
			$("#sidebar:last-child").css('color', colors[markers[marker].event_num][1]);
		}
	}
}

window.onload = function() {
	info = new google.maps.InfoWindow();
	for (var i = 0; i < colors.length; i++) {
		icons.push({
			fillColor: colors[i][0],
			fillOpacity: 1,
			strokeColor: colors[i][1],
			strokeWeight: 1,
			path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
			scale: 4
		});
	}

	default_icon = {
		strokeColor: "#000000",
		strokeWeight: 1,
		path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
		scale: 4
	};

	var check = true;
	google.maps.event.addListener(map, 'mousemove', function (event) {
			if (check)
			{
				var mouse_lat = event.latLng.lat();
				var mouse_lng = event.latLng.lng();

				var lat_distance, lng_distance, distance;
				for (var marker in markers)
				{
					lat_distance = mouse_lat-markers[marker].getPosition().lat();
					if (lat_distance < .01 && lat_distance > -.01)
					{
						lng_distance = mouse_lng-markers[marker].getPosition().lng();
						if (lng_distance < .01 && lng_distance > -.01)
						{
							distance = Math.pow(lat_distance*lat_distance+lng_distance*lng_distance, 0.5);
							if (distance < .01)
							{
								highlight(marker);
								continue;
							}
						}
					}
					dim(marker);
				}
				check = false;
				setTimeout(function(){check=true;}, 10);
			}
		});

	poll();
};