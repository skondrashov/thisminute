### Installation
1) Be on Ubuntu 16.04

2) Paste the following into a terminal:
```
wget -qO - https://download.sublimetext.com/sublimehq-pub.gpg | sudo apt-key add -;\
echo "deb https://download.sublimetext.com/ apt/stable/" | sudo tee /etc/apt/sources.list.d/sublime-text.list;\
sudo apt-get update;\
sudo apt-get -y install git sublime-text mysql-client python-pip;\
git clone --recursive https://github.com/tkondrashov/thisminute ~/thisminute
```

3)
Add the following lines to the end of your .bashrc file (`subl ~/.bashrc` in Terminal to open). This will set you up for a local pericog installation which is most likely what you want. However, you can edit them to point to other servers ie `TM_PERICOG_ADDRESS="pericog.thisminute.org"`.
```
TM_MYSQL_ROOT_PASSWORD="paradise"
TM_SENTINEL_ADDRESS="thisminute.org"
TM_ARCHIVIST_ADDRESS="archivist.thisminute.org"
TM_PERICOG_ADDRESS="localhost"
. ~/thisminute/util/bash_aliases.sh
```

4) To install pericog, run this script on the machine you want pericog on (usually your machine). You will have to enter a password for your mysql root user. This MUST be the TM_MYSQL_ROOT_PASSWORD from step 3 above.
```
sudo mkdir /srv;\
sudo chmod 777 /srv;\
sudo apt-get -y install mysql-server;\
sudo pip install mysql-connector==2.1.4 numpy scipy unidecode gensim tensorflow-gpu;\
pericog_init
```


pericog compile command:
g++-7 -I/srv/lib/mysql-connector-cpp/include -I/srv/lib/boost -I/srv/lib/inih/cpp -I/usr/include/cppconn -I/srv/lib -Wall -Werror -pedantic -std=c++14 /srv/etc/pericog.cpp /srv/lib/inih/cpp/INIReader.cpp /srv/lib/inih/ini.c -o /srv/bin/pericog -L/usr/lib -lmysqlcppconn -lpthread -O3

