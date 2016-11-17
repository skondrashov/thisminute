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

function updateList(newData, oldData, dataType)
{
	for (var id in oldData)
	{
		if (oldData.hasOwnProperty(id))
		{
			oldData[id].keep = false;
		}
	}

	for (var i = 0; i < newData.length; i++)
	{
		var id = dataType.generateId(newData[i]);

		if (!oldData.hasOwnProperty(id))
		{
			oldData[id] = new dataType(newData[i]);
		}
		oldData[id].keep = true;
	}

	for (var id in oldData)
	{
		if (oldData.hasOwnProperty(id))
		{
			if (!oldData[id].keep)
			{
				if (oldData.hasOwnProperty("destroy"))
					oldData[id].destroy();
				delete oldData[id];
			}
		}
	}
}

function EventMarker(data, id)
{
	var t = this;
	var marker = new google.maps.Marker({
			position: {lat: parseFloat(data.lat), lng: parseFloat(data.lon)},
			map: map,
			icon: default_icon
		});
	marker.highlighted = false;
	marker.text = data.text;

	marker.addListener('click', function() {
		});

	marker.addListener('mouseover', function() {
			if (marker.highlighted)
				return;
			marker.highlighted = true;
			marker.setIcon(highlighted_icon);
			$("#sidebar").prepend($('<div id="tweet_infobox_' + id + '" class="tweet_infobox infobox">' + marker.text + '</div>"'));
		});

	marker.addListener('mouseout', function() {
			if (!marker.highlighted)
				return;
			marker.highlighted = false;
			marker.setIcon(default_icon);
			$("#tweet_infobox_" + id).remove();
		});

	t.destroy = function() {
			marker.setMap(null);
		};
}

EventMarker.generateId = function(data) {
	return data.id;
};

function TweetInfobox(data, id)
{
	var t = this;
	var tweet = {};
	tweet.id = id;
	$("#sidebar").prepend($('<div id="tweet' + id + '" class="infobox">' + result[i].text + '</div>"'));
	t.destroy = function () {
			$("#tweet_" + tweet.id).remove();
		};
}

TweetInfobox.generateId = function(data) {
	return (result[i].time + result[i].text).hashCode();
};

function poll() {
	xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {
		if (xhttp.readyState == 4 && xhttp.status == 200)
		{
			updateList(JSON.parse(xhttp.responseText).events, markers, EventMarker);
			updateList(JSON.parse(xhttp.responseText).tweets, );

			result = JSON.parse(xhttp.responseText).tweets;
			ids = [];
			for (var i = 0; i < result.length; i++)
			{

				// only create a new marker if its id has not been filled
				if (!(id in tweets))
				{
				}
			}

			// remove tweets that exist locally but were not passed from the server
			for (var tweet in tweets)
			{
				if (tweets.hasOwnProperty(tweet))
				{
					if (ids.indexOf(tweet) === -1)
					{
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