<!doctype HTML>
<html>
	<head>
		<title>ThisMinute Event Mapping</title>
		<meta charset="utf-8">
		<link rel="stylesheet" href="css/map.css">
	</head>
	<body>
		<script src="https://code.jquery.com/jquery-2.2.4.min.js" integrity="sha256-BbhdlvQf/xTY9gja0Dq3HiwQF8LaCRTXxZKRutelT44=" crossorigin="anonymous"></script>
		<script src="lib/poll.js"></script>
		<div id="header">ThisMinute</div>
		<div id="box">
			<div id="map"></div>
			<div id="sidebar">
				<div id="columns" class="infobox">
					<div class="tweet">
						<div id="count" class="text"></div>
						<div id="vote_description">
							<div class="spam">
								<div class="up hidden">
									Spam tweets exist primarily to attract attention to something
								</div>
								<div class="down hidden">
									Nonspam tweets exist primarily to inform about something
								</div>
							</div>
							<div class="fiction">
								<div class="up hidden">
									Fiction is about something not in the real world
								</div>
								<div class="down hidden">
									Nonfiction is about the real world
								</div>
							</div>
							<div class="poetry">
								<div class="up hidden">
									Poetry conveys meaning through the emotional associations of words
								</div>
								<div class="down hidden">
									Prose has literal meaning
								</div>
							</div>
							<div class="use">
								<div class="up hidden">
									tweets that Use their words intend to say what the words mean
								</div>
								<div class="down hidden">
									tweets that Mention their words intend to talk about the words mentioned
								</div>
							</div>
							<div class="event">
								<div class="up hidden">
									Event tweets are about the world changing state - events have a before and after, but are not necessarily momentary
								</div>
								<div class="down hidden">
									Nonevent tweets don't talk about an event
								</div>
							</div>
							<div class="disaster">
								<div class="up hidden">
									Disaster tweets are about damage to people or property, with an exception to socially sanctioned destruction (controlled demolitions and similar)
								</div>
								<div class="down hidden">
									Nondisaster tweets don't refer to anything involving damage to people or property
								</div>
							</div>
							<div class="personal">
								<div class="up hidden">
									Personal tweets appear on personal accounts
								</div>
								<div class="down hidden">
									Official tweets appear on official accounts
								</div>
							</div>
							<div class="eyewitness">
								<div class="up hidden">
									Eyewitness tweets contain information acquired directly from the world by the author, unfiltered through other people
								</div>
								<div class="down hidden">
									Secondhand tweets contain information about the world gained through another human being or organization
								</div>
							</div>
							<div class="secondhand">
								<div class="up hidden">
									Secondhand (Personal) tweets have secondhand information gained through a personal source
								</div>
								<div class="down hidden">
									Secondhand (Media) tweets have secondhand information gained through a media source
								</div>
							</div>
							<div class="breaking">
								<div class="up hidden">
									Breaking news tweets are intended to inform about a fact in itself
								</div>
								<div class="down hidden">
									Expository tweets are intended to add information to a fact that may already be known to a reader
								</div>
							</div>
							<div class="informative">
								<div class="up hidden">
									Informative tweets contain information that is likely to be new to twitter
								</div>
								<div class="down hidden">
									Uninformative tweets contain no information, or information that is widely accessible online
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<script async defer
			src="https://maps.googleapis.com/maps/api/js?key=AIzaSyB2qLQUWCQ-IcHvOFHdxmFvCdzQ5wqt73I&callback=initMap">
		</script>
	</body>
</html>
