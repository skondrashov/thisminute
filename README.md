### Installation

[![Join the chat at https://gitter.im/thisminute/community](https://badges.gitter.im/thisminute/community.svg)](https://gitter.im/thisminute/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

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
