#pragma once

#include <string>
#include <regex>
#include <fstream>
#include <algorithm>
#include <map>
#include <unordered_set>
#include <unordered_map>
#include <cassert>
#include <cmath>
#include <vector>
#include <iostream>
#include <vector>
#include <memory>
#include <utility>
#include <thread>
#include <mutex>
#include <queue>
#include <ctime>
#include <iterator>

#include "mysql_connection.h"

#include <cppconn/driver.h>
#include <cppconn/exception.h>
#include <cppconn/resultset.h>
#include <cppconn/statement.h>

#include "INIReader.h"
#include "timer.h"

using namespace std;

struct Tweet
{
	bool processed = false;
	bool require_core_distance_update = true;
	double core_distance;

	double lat, lon;
	unsigned int time;
	unordered_set<string> text;
	string id;
	multimap<double, unique_ptr<Tweet>> neighbors;
	unordered_map<unique_ptr<Tweet>, double> distances;

	Tweet(string time, string lat, string lon, string user, string _text);
};

// utility functions
unordered_set<string> explode(string const &s);
template<typename T> void getArg(T &arg, string section, string option);

// YEAH LET'S DO IT
void Initialize(int argc, char* argv[]);
void updateTweets(unordered_set<unique_ptr<Tweet>> &tweets);
void updateLastRun();
void compareTweets(const unique_ptr<Tweet> &a, const unique_ptr<Tweet> &b);
