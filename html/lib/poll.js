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
			var result = JSON.parse(xhttp.responseText).events;
			var ids = [];
			for (var i = 0; i < result.length; i++)
			{
				// create unique id for each tweet received to ensure we don't create duplicates
				var id = ids[i] = result[i].id;

				// only create a new marker if its id has not been filled
				if (!(id in markers))
				{
					markers[id] = new google.maps.Marker({
							position: {lat: parseFloat(result[i].lat), lng: parseFloat(result[i].lon)},
							map: map,
							icon: default_icon
						});
					markers[id].event_num = result[i].event_id;
					markers[id].highlighted = false;
					markers[id].text = result[i].text;
					markers[id].id = id;

					(function() {
						var marker = markers[id];
						marker.addListener('click', function() {
							});
						marker.addListener('mouseover', function() {
								if (marker.highlighted)
									return;
								marker.highlighted = true;
								marker.setIcon(highlighted_icon);
								$("#sidebar").append($('<div id="marker_' + marker.id + '" class="infobox">' + marker.text + '</div>"'));
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

			result = JSON.parse(xhttp.responseText).tweets;
			ids = [];
			for (var i = 0; i < result.length; i++)
			{
				// create unique id for each tweet received to ensure we don't create duplicates
				var id = ids[i] = "tweet_" + (result[i].time + result[i].text).hashCode();

				// only create a new marker if its id has not been filled
				if (!(id in tweets))
				{
					tweets[id] = {};
					tweets[id].id = id;
					$("#sidebar").prepend($('<div id="tweet' + id + '" class="infobox">' + result[i].text + '</div>"'));
				}
			}

			// remove tweets that exist locally but were not passed from the server
			for (var tweet in tweets)
			{
				if (tweets.hasOwnProperty(tweet))
				{
					if (ids.indexOf(tweet) === -1)
					{
						$("#tweet_" + tweet.id).remove();
					}
				}
			}
		}
	};
	xhttp.open("GET", "press/get_markers.php", true);
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