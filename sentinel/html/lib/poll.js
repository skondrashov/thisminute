var latest_server_events, latest_server_tweets;

var map, markers = {}, tweets = {}, info, xhttp, default_icon, highlighted_icon;

var vote_mode = false;

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
			icon: highlighted_icon
		});
	var highlighted = true;

	$("#columns").after($(`
			<div id="marker_${id}" class="infobox"></div>
		`));
	for (var tweet of tweets)
	{
		$(`#marker_${id}`).append($(`
				<div id="tweet_${tweet.id}" class="tweet">
					<div class="text">
						<div class="x">x</div>
						${tweet.text}
					</div>`
					// <div class="vote spam">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					// <div class="vote fiction">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					// <div class="vote poetry">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					// <div class="vote use">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					// <div class="vote event">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					+`<div class="vote disaster">
						<div class="up"></div>
						<div class="down"></div>
					</div>`+
					// <div class="vote personal">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					// <div class="vote eyewitness">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					// <div class="vote secondhand">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					// <div class="vote breaking">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
					// <div class="vote informative">
					// 	<div class="up"></div>
					// 	<div class="down"></div>
					// </div>
				`</div>
			`));
	}

	if (!vote_mode) {
		$(`#marker_${id}`).find('.vote, .x').addClass('hidden');
	}

	marker.addListener('click', function() {
		});
	marker.addListener('mouseover', function() {
		});
	marker.addListener('mouseout', function() {
		});
	return marker;
}

function poll() {
	$.ajax({
		url: "sentinel/get_markers.php"
	}).done(function(data) {
		var ids = [];
		var data = JSON.parse(data);
		$('#count').html(data.count[0].count);

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
	if (!vote_mode) {
		setTimeout(poll, 800);
	}
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

	$(document).keypress(function(e) {
		if (e.which == 118) {
			if (vote_mode) {
				$('.vote, .x').addClass('hidden');
				vote_mode = false;
				poll();
			} else {
				$('.vote, .x').removeClass('hidden');
				vote_mode = true;
			}
		}
	});

	$(document).on("click", ".x", function() {
		var element = $(this);
		$.ajax({
			url: "sentinel/vote.php",
			method: "POST",
			data: {
				id: element.closest('.tweet').attr('id').split("_")[1],
				submit: true
			}
		}).done(function(data) {
			poll();
		});
	});

	var properties = [
		'spam',
		'fiction',
		'poetry',
		'use',
		'event',
		'disaster',
		'personal',
		'eyewitness',
		'secondhand',
		'breaking',
		'informative'
	];

	$(document).on("click", ".vote>div", function() {
		var element = $(this);

		var data = {
			id: element.closest('.tweet').attr('id').split("_")[1]
		};

		for (property of properties) {
			if (element.parent().hasClass(property)) {
				data[property] = element.hasClass('up');
			}
		}

		$.ajax({
			url: "sentinel/vote.php",
			method: "POST",
			data: data
		}).done(function(data) {
			if (data != 'success') {
				return;
			}
			element.siblings().removeClass('voted');
			element.addClass('voted');
		});
	});

	$(document).on("mouseover", ".vote>div", function() {
		let $el = $(this);
		for (property of properties) {
			if ($el.parent().hasClass(property)) {
				$('#vote_description .' + property).children($el.hasClass('up') ? '.up' : '.down').show();
			}
		}
	});

	$(document).on("mouseout", ".vote>div", function() {
		$('#vote_description').children().children().hide();
	});

	poll();
};
