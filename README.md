pericog compile command:

g++-4.9 -I/srv/lib/connector/include -I/srv/lib/boost_1_60_0 -I/srv/lib/inih/cpp -I/usr/include/cppconn -I/srv/etc/lib -Wall -Werror -pedantic -std=c++14 /srv/etc/daemons/pericog.cpp /srv/lib/inih/cpp/INIReader.cpp -o /srv/bin/pericog -L/usr/lib -lmysqlcppconn -lpthread -O3