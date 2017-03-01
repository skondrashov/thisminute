#pragma once

#include <string>
#include <vector>
#include <regex>
#include <fstream>
#include <algorithm>
#include <map>
#include <unordered_set>
#include <unordered_map>
#include <cassert>
#include <cmath>
#include <iostream>
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
#include "tweet.h"
#include "util.h"

using namespace std;

struct Cell
{
	static vector<vector<Cell>> cells;

	unsigned int x, y;
	unordered_map<string, unordered_set<Tweet*>> tweets_by_word;
	vector<Cell*> region;
};

// utility functions
unordered_set<string> explode(string const &s);
string getArg(string section, string option);
void getArg(unsigned int &arg, string section, string option);
void getArg(double &arg, string section, string option);
void getArg(string &arg, string section, string option);

// core functionality
void Initialize();
void updateTweets(deque<Tweet*> &tweets);
double getDistance(const vector<double> &A, const vector<double> &B);
vector<vector<Tweet*>> getClusters(const deque<Tweet*> &tweets);
void writeClusters(vector<vector<Tweet*>> &clusters);
void updateLastRun();
