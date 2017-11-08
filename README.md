don't forget to clone recursively! this project contains boost as a submodule, so expect cloning to take a long time (~40 min)
`git clone --recursive https://github.com/tkondrashov/ThisMinute`


/util/bash_aliases.sh has convenient aliases for setting up the remote servers. add the following lines to .bashrc to access them from your terminal (logout required):

```
export TM_BASE_PATH=<path to ThisMinute repo>
export TM_KEY_PATH=<path to ThisMinute private key>
. $TM_BASE_PATH/util/bash_aliases.sh
```


###pericog
pericog server requires
```
sudo apt-get install python-pip g++-4.9 libmysqlcppconn-dev
pip install mysql-connector==2.1.4 numpy scipy unidecode
pip install gensim
```

pericog compile command:
g++-4.9 -I/srv/lib/mysql-connector-cpp/include -I/srv/lib/boost -I/srv/lib/inih/cpp -I/usr/include/cppconn -I/srv/lib -Wall -Werror -pedantic -std=c++14 /srv/etc/pericog.cpp /srv/lib/inih/cpp/INIReader.cpp /srv/lib/inih/ini.c -o /srv/bin/pericog -L/usr/lib -lmysqlcppconn -lpthread -O3
