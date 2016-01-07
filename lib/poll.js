var map, markers = {}, info;
function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: {lat: 40.712783, lng: -74.005942},
		zoom: 12
	});
}

window.onload = function() {
	var xhttp;
	info = new google.maps.InfoWindow();
	window.setInterval(function(){
		xhttp = new XMLHttpRequest();
		xhttp.onreadystatechange = function() {
			if (xhttp.readyState == 4 && xhttp.status == 200) {
				var result = JSON.parse(xhttp.responseText);
				var ids = [];

				for (var i = 0; i < result.length; i++)
				{
					// create unique id for each tweet received to ensure we don't create duplicates
					var id = ids[i] = result[i][0] + result[i][1] + result[i][2] + result[i][3];

					// only create a new marker if its id has not been filled
					if (!(id in markers))
					{
						markers[id] = new google.maps.Marker({
								position: {lat: parseFloat(result[i][1]), lng: parseFloat(result[i][2])},
								map: map,
								title: result[i][0]
							});

						(function() {
							var content = result[i][3];
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
		xhttp.open("GET", "sample.php", true);
		xhttp.send();
	}, 1000); 
};