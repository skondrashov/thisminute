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
#include <chrono>
#include <mutex>
#include <queue>
#include <ctime>
#include <iterator>
#include <unistd.h>

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
	bool require_update = true;
	double core_distance, smallest_reachability_distance;

	double lat, lon;
	unsigned int x, y, time;
	unordered_set<string> words;
	string text;
	multimap<double, Tweet*> optics_neighbors;
	unordered_map<Tweet*, double> optics_distances;
	unordered_map<string, double> regional_word_rates;

	Tweet(string _time, string _lat, string _lon, string _text);
	~Tweet();
};

struct Cell
{
	static vector<vector<Cell>> cells;

	unsigned int tweet_count = 0, x, y;
	unordered_map<string, unordered_set<Tweet*>> tweets_by_word;
	vector<Cell*> region;
};

// utility functions
unordered_set<string> explode(string const &s);
template<typename T> void getArg(T &arg, string section, string option);

// YEAH LET'S DO IT
void Initialize(int argc, char* argv[]);
void updateTweets(deque<Tweet*> &tweets);
double getOpticsDistance(const Tweet &a, const Tweet &b);
vector<Tweet*> getReachabilityPlot(const deque<Tweet*> &tweets);
vector<vector<Tweet*>> extractClusters(vector<Tweet*> reachability_plot);
void updateLastRun();
