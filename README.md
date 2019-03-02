### About

[![Join the chat at https://gitter.im/thisminute/community](https://badges.gitter.im/thisminute/community.svg)](https://gitter.im/thisminute/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

## Sentinel
The UI and APIs of http://thisminute.org
Press v to enter a sentiment tagging mode, and hover over each arrow for the sentiment it describes. Your IP has to be whitelisted to actually be able to submit the votes, so the arrows won't do anything. The sentiments are abstract ways to split up some concepts of language. The tweets you see on the map are just miscellaneous tweets selected for tagging, when the twitter stream is up they update in real time, and when Pericog is running it tries to filter with the model trained on the tagged data.
http://thisminute.org/sentinel/get_tweet.php?n=30&format=1 will give you the last 30 tweets in the database in human-readable format (you can mess with the GET parameters).
The code for this portion of the project is named "sentinel", you can find the version that should be what's on the server in sentinel/html, and the get_tweet API and a couple of others in sentinel/html/sentinel.

## Archivist
Pulls tweets from Twitter
Mostly just an external library. There is some custom code in archivist.php and lib/Consumer.php but it's just some formatting and the DB insert calls.

## Pericog
The "intelligent" tweet filter
Currently sentinel is in this data tagging mode where it just displays some miscellaneous selection of tweets. The results when it was running were interesting, but not cutting-edge or anything I'd put on a production site. I'd love to get enough data to train it on my sentiments as a next step and attempt a leap in NLP theory rather than settling for a commercial sentiment analysis tool. If you are interested in helping with data tagging, contact me!

### Installation


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
