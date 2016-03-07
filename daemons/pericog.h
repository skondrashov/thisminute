#pragma once

#include <string>
#include <regex>
#include <fstream>
#include <algorithm>
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

#include "mysql_connection.h"

#include <cppconn/driver.h>
#include <cppconn/exception.h>
#include <cppconn/resultset.h>
#include <cppconn/statement.h>

#include "INIReader.h"
#include "timer.h"

using namespace std;

template<class T>
using Grid = vector<vector<T>>;

template<class T>
using WordToGridMap = unordered_map<string, Grid<T>>;

struct Tweet
{
	Tweet(int x, int y, string text) :
		x(x), y(y), text(text) {}

	int x, y;
	string text;
};

// utility functions
unordered_set<string> explode(string const &s);
template<typename T> Grid<T> makeGrid();
template<typename T> void getArg(T &arg, string section, string option);
Grid<double> gaussBlur(const Grid<double> &unblurred_array);

struct Stats
{
	struct StatsPerWord
	{
		Grid<int> currentCounts;
		Grid<double> currentRates, historicMeanRates, historicDeviations;
		double currentGlobalRate;
		StatsPerWord() :
			currentGlobalRate(0)
		{
			currentCounts      = makeGrid<int>();
			currentRates       = makeGrid<double>();
			historicMeanRates  = makeGrid<double>();
			historicDeviations = makeGrid<double>();
		}
	};

	Grid<int> tweetCounts;
	unordered_map<string, StatsPerWord> perWord;

	Stats()
	{
		tweetCounts = makeGrid<int>();
	}
};

// YEAH LET'S DO IT
void Initialize(int argc, char* argv[]);
bool readCache(Stats &stats);
unordered_map<int, Tweet> getUserIdToTweetMap();
Grid<int> refineTweetsAndGetTweetCountPerCell(unordered_map<int, Tweet> &userIdTweetMap);
void getCurrentWordCountPerCell(Stats &stats, const unordered_map<int, Tweet> &userIdTweetMap);
void getCurrentLocalAndGlobalRatesForWord(Stats &stats);
void getHistoricWordRatesAndDeviation(Stats &stats);
void commitStats(const Stats &stats);
void detectEvents(const Stats &stats);
