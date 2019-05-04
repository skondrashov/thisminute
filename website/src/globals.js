window.tm = {};
window.tm.sentiments = [
		{
			key: "spam",
			up:   "Spam tweets exist primarily to attract attention to something",
			down: "Nonspam tweets exist primarily to inform about something"
		},
		{
			key: "fiction",
			up:   "Fiction is about something not in the real world",
			down: "Nonfiction is about the real world"
		},
		{
			key: "poetry",
			up:   "Poetry conveys meaning through the emotional associations of words",
			down: "Prose has literal meaning"
		},
		{
			key: "use",
			up:   "tweets that Use their words intend to say what the words mean",
			down: "tweets that Mention their words intend to talk about the words mentioned"
		},
		{
			key: "event",
			up:   "Event tweets are about the world changing state - events have a before and after, but are not necessarily momentary",
			down: "Nonevent tweets don't talk about an event"
		},
		{
			key: "disaster",
			up:   "Disaster tweets are about damage to people or property, with an exception to socially sanctioned destruction (controlled demolitions and similar)",
			down: "Nondisaster tweets don't refer to anything involving damage to people or property"
		},
		{
			key: "personal",
			up:   "Personal tweets appear on personal accounts",
			down: "Official tweets appear on official accounts"
		},
		{
			key: "eyewitness",
			up:   "Eyewitness tweets contain information acquired directly from the world by the author, unfiltered through other people",
			down: "Secondhand tweets contain information about the world gained through another human being or organization"
		},
		{
			key: "secondhand",
			up:   "Secondhand (Personal) tweets have secondhand information gained through a personal source",
			down: "Secondhand (Media) tweets have secondhand information gained through a media source"
		},
		{
			key: "breaking",
			up:   "Breaking news tweets are intended to inform about a fact in itself",
			down: "Expository tweets are intended to add information to a fact that may already be known to a reader"
		},
		{
			key: "informative",
			up:   "Informative tweets contain information that is likely to be new to twitter",
			down: "Uninformative tweets contain no information, or information that is widely accessible online"
		}
	];
