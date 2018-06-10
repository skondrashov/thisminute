var latest_server_events, latest_server_tweets;

var map, markers = {}, tweets = {}, info, xhttp, default_icon, highlighted_icon;

function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: {lat: 39.8333333, lng: -98.585522},
		zoom: 5
	});
}

function createMarker(lon, lat, text, id, tweets) {
	var marker = new google.maps.Marker({
			position: {lat: parseFloat(lat), lng: parseFloat(lon)},
			map: map,
			icon: default_icon
		});
	var highlighted;

	marker.addListener('click', function() {
			if (highlighted)
			{
				highlighted = false;
				marker.setIcon(default_icon);
				$(`#marker_${id}`).remove();
			}
			else
			{
				highlighted = true;
				marker.setIcon(highlighted_icon);
				$("#sidebar").append($(`
						<div id="marker_${id}" class="infobox"></div>
					`));
				for (var tweet of tweets)
				{
					$(`#marker_${id}`).append($(`
							<div id="tweet_${tweet.id}" class="tweet">
								<div class="text">
									${tweet.text}
								</div>
								<div class="vote">
									<div class="up"></div>
									<div class="down"></div>
								</div>
							</div>
						`));
				}
			}
		});
	marker.addListener('mouseover', function() {
		});
	marker.addListener('mouseout', function() {
		});
	return marker;
}

String.prototype.hashCode = function() {
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
	$.ajax({
		url: "sentinel/get_markers.php"
	}).done(function(data) {
		var ids = [];
		var data = JSON.parse(data);
		for (var event of data.events)
		{
			// create unique id for each tweet received to ensure we don't create duplicates
			// even numbers only to prevent collision with odd numbers
			var id = event.id << 1;
			ids.push(id.toString());

			if (!(id in markers))
			{
				markers[id] = createMarker(event.lon, event.lat, event.text, id, event.tweets);
			}
		}

		for (var tweet of data.tweets)
		{
			// odd numbers only to prevent collision with even numbers
			var id = tweet.id << 1 + 1;
			ids.push(id.toString());

			if (!(id in tweets))
			{
				tweets[id] = true;
				if (tweet.event_id)
				{
					markers[tweet.event_id].tweets.push(tweet);
				}
				else
				{
					markers[id] = createMarker(tweet.lon, tweet.lat, tweet.text, id, [tweet]);
				}
			}
		}

		// remove markers that exist locally but were not passed from the server
		for (var id in markers)
		{
			if (markers.hasOwnProperty(id))
			{
				if (ids.indexOf(id) === -1)
				{
					$(`#marker_${id}`).remove();
					markers[id].setMap(null);
					delete markers[id];
				}
			}
		}
	});
	setTimeout(poll, 1000);
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

	$(document).on("click", ".vote>div", function() {
		var element = $(this);
		$.ajax({
			url: "sentinel/vote.php",
			method: "POST",
			data: {
				id: element.closest('.tweet').attr('id').split("_")[1],
				vote: element.hasClass('up')
			}
		}).done(function(data) {
			if (data != 'success') {
				return;
			}
			element.addClass('voted');
		});
	});

	poll();
};
