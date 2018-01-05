var latest_server_events, latest_server_tweets;

var map, markers = {}, tweets = {}, info, xhttp, default_icon, highlighted_icon;

function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: {lat: 39.8333333, lng: -98.585522},
		zoom: 5
	});
}

String.prototype.hashCode = function(){
	var hash = 0;
	if (this.length == 0) return hash;
	for (i = 0; i < this.length; i++) {
		char = this.charCodeAt(i);
		hash = ((hash<<5)-hash)+char;
		hash = hash & hash; // Convert to 32bit integer
	}
	return hash;
}

function poll() {
	xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {
		if (xhttp.readyState == 4 && xhttp.status == 200)
		{
			var ids = [];
			for (var event of JSON.parse(xhttp.responseText).events)
			{
				// create unique id for each tweet received to ensure we don't create duplicates
				var id = event.id;
				ids.push(id);

				// only create a new marker if its id has not been filled
				if (!(id in markers))
				{
					markers[id] = new google.maps.Marker({
							position: {lat: parseFloat(event.lat), lng: parseFloat(event.lon)},
							map: map,
							icon: default_icon
						});
					markers[id].highlighted = false;
					markers[id].text = event.text;
					markers[id].id = id;
					markers[id].tweets = [];

					(function() {
						var marker = markers[id];
						marker.addListener('click', function() {
							});
						marker.addListener('mouseover', function() {
								if (marker.highlighted)
									return;
								marker.highlighted = true;
								marker.setIcon(highlighted_icon);
								$("#sidebar").append($('<div id="marker_' + marker.id + '" class="infobox"></div>"'));
								for (var tweet of marker.tweets)
								{
									$("#marker_" + marker.id).append($('<div id="tweet_' + id + '" class="infobox">' + tweet.text + '</div>"'));
								}
							});
						marker.addListener('mouseout', function() {
								if (!marker.highlighted)
									return;
								marker.highlighted = false;
								marker.setIcon(default_icon);
								$("#marker_" + marker.id).remove();
							});
					})();
				}
			}

			// remove markers that exist locally but were not passed from the server
			for (var id in markers)
			{
				if (markers.hasOwnProperty(id))
				{
					if (ids.indexOf(id) === -1)
					{
						markers[id].setMap(null);
						delete markers[id];
					}
				}
			}

			for (var tweet of JSON.parse(xhttp.responseText).tweets)
			{
				var id = "tweet_" + (tweet.time + tweet.text).hashCode();
				// only create a new marker if its id has not been filled
				if (!(id in tweets))
				{
					tweets[id] = true;
					markers[tweet.event_id].tweets.push(tweet);
				}
			}
		}
	};
	xhttp.open("GET", "sentinel/get_markers.php", true);
	xhttp.send();
	setTimeout(poll, 5000);
}

window.onload = function() {
	info = new google.maps.InfoWindow();
	highlighted_icon = {
			fillColor: "#F77",
			fillOpacity: 1,
			strokeColor: "#222",
			strokeWeight: 1,
			path: google.maps.SymbolPath.CIRCLE,
			scale: 10
		};
	default_icon = {
			fillColor: "#F88",
			fillOpacity: .7,
			strokeColor: "#222",
			strokeWeight: 1,
			path: google.maps.SymbolPath.CIRCLE,
			scale: 10
		};

	poll();
};
