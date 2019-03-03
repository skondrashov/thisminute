# About

[![Join the chat at https://gitter.im/thisminute/community](https://badges.gitter.im/thisminute/community.svg)](https://gitter.im/thisminute/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

## Sentinel
The UI and APIs of http://thisminute.org/
Press v to enter a sentiment tagging mode, and hover over each arrow for the sentiment it describes. Your IP has to be whitelisted to actually be able to submit the votes, so the arrows won't do anything. The sentiments are abstract ways to split up some concepts of language. The tweets you see on the map are just miscellaneous tweets selected for tagging, when the twitter stream is up they update in real time, and when Pericog is running it tries to filter with the model trained on the tagged data.
http://thisminute.org/sentinel/get_tweet.php?n=30&format=1 will give you the last 30 tweets in the database in human-readable format (you can mess with the GET parameters).
The code for this portion of the project is named "sentinel", you can find the version that should be what's on the server in sentinel/html, and the get_tweet API and a couple of others in sentinel/html/sentinel.

## Archivist
Pulls tweets from Twitter
Mostly just an external library. There is some custom code in archivist.php and lib/Consumer.php but it's just some formatting and the DB insert calls.

## Pericog
The "intelligent" tweet filter
Currently sentinel is in this data tagging mode where it just displays some miscellaneous selection of tweets. The results when it was running were interesting, but not cutting-edge or anything I'd put on a production site. I'd love to get enough data to train it on my sentiments as a next step and attempt a leap in NLP theory rather than settling for a commercial sentiment analysis tool. If you are interested in helping with data tagging, contact me!

I am attempting to train my sentiment analysis using a combination of sentiments rather than one pure "is this an event tweet?" sentiment. Here are the sentiment classes and their descriptions. The ideal tweet is informative nonspam nonfiction prose, uses its words (as opposed to mentioning them, see https://en.wikipedia.org/wiki/Use%E2%80%93mention_distinction), is about an event, is either eyewitness or secondhand from a nonmedia source, and is breaking new information. Whether the tweet is about a disaster or not is not important to whether the tweet is good, but I want to start with disaster tweets because I expect that classifier to be much easier to train than some others, and that information to be more useful to the world.

### Spam/Nonspam
- Spam tweets exist primarily to attract attention to something
- Nonspam tweets exist primarily to inform about something

### Fiction/Nonfiction
- Fiction is about something not in the real world
- Nonfiction is about the real world

### Poetry/Prose
- Poetry conveys meaning through the emotional associations of words
- Prose has literal meaning

### Use/Mention
- tweets that Use their words intend to say what the words mean
- tweets that Mention their words intend to talk about the words mentioned

### Event/Nonevent
- Event tweets are about a change of state - events have a before and after, but are not necessarily momentary
- Nonevent tweets don't talk about an event

### Disaster/Nondisaster
- Disaster tweets are about damage to people or property, with an exception to socially sanctioned destruction (controlled demolitions and similar)
- Nondisaster tweets don't refer to anything involving damage to people or property

### Personal/Official
- Personal tweets appear on personal accounts
- Official tweets appear on official accounts

### Eyewitness/Secondhand
- Eyewitness tweets contain information acquired directly from the world by the author, unfiltered through other people
- Secondhand tweets contain information about the world gained through another human being or organization

### Secondhand (Personal)/Secondhand (Media)
- Secondhand (Personal) tweets have secondhand information gained through a personal source
- Secondhand (Media) tweets have secondhand information gained through a media source

### Breaking/Expository
- Breaking news tweets are intended to inform about a fact in itself
- Expository tweets are intended to add information to a fact that may already be known to a reader

### Informative/Uninformative
- Informative tweets contain information that is likely to be new to twitter
- Uninformative tweets contain no information, or information that is widely accessible online

# Installation

1) Be on Ubuntu 16.04

2) Paste the following into a terminal:
```
wget -qO - https://download.sublimetext.com/sublimehq-pub.gpg | sudo apt-key add -;\
echo "deb https://download.sublimetext.com/ apt/stable/" | sudo tee /etc/apt/sources.list.d/sublime-text.list;\
sudo apt-get update;\
sudo apt-get -y install git sublime-text postgresql-client python-pip;\
git clone --recursive https://github.com/tkondrashov/thisminute ~/thisminute;\
subl ~/thisminute
```

3) Add the following lines to the end of your .bashrc file (`subl ~/.bashrc` in Terminal to open):
```
PERICOG_SQL_ROOT_PASSWORD="paradise"
TM_SENTINEL_ADDRESS="tkondrashov@thisminute.org"
TM_ARCHIVIST_ADDRESS="tkondrashov@archivist.thisminute.org"
TM_PERICOG_ADDRESS="localhost"
. ~/thisminute/util/bash_aliases.sh
```
This will set you up for a local pericog installation which is most likely what you want. You can make edits to change your password or point to other servers (ie `TM_PERICOG_ADDRESS="pericog.thisminute.org"`).

4) Acquire or create an auth folder for your needs. This will go in ~/thisminute/auth and have a folder structure similar to this:
```
auth
	sql
		archivist.pw
		pericog.pw
		sentinel.pw
	ssl
		tm.pem
		tweets-usa
			client-cert.pem
			client-key.pem
			server-ca.pem
	twitter
		access_token
		access_token_secret
		consumer_key
		consumer_secret
```
You might not have a twitter directory or sql/archivist.pw, and you may be connecting to a different tweets server than tweets-usa.

5) To install pericog, run `pericog_init`.


pericog compile command:
g++-7 -I/srv/lib/mysql-connector-cpp/include -I/srv/lib/boost -I/srv/lib/inih/cpp -I/usr/include/cppconn -I/srv/lib -Wall -Werror -pedantic -std=c++14 /srv/etc/pericog.cpp /srv/lib/inih/cpp/INIReader.cpp /srv/lib/inih/ini.c -o /srv/bin/pericog -L/usr/lib -lmysqlcppconn -lpthread -O3
