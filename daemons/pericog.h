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

// SQL functions
string sqlAppendRates(const string &word, const Grid<double> &wordRates);
void commitRates(const string &sqlValuesString);


// YEAH LET'S DO IT
void Initialize(int argc, char* argv[]);

unordered_map<int, Tweet> getUserIdToTweetMap();

Grid<int> refineTweetsAndGetTweetCountPerCell(unordered_map<int, Tweet> &userIdTweetMap);

unordered_map <string, Grid<int>> getCurrentWordCountPerCell(const unordered_map<int, Tweet> &userIdTweetMap);

pair<WordToGridMap<double>, WordToGridMap<double>> getHistoricWordRatesAndDeviation();

pair<Grid<double>, double> getCurrentLocalAndGlobalRatesForWord(const Grid<int> &wordCountPerCell, const Grid<int> &tweetCountPerCell);

Grid<double> gaussBlur(const Grid<double> &unblurred_array);

void detectEvents(
	const WordToGridMap<int> &currentWordCountPerCell,
	const WordToGridMap<double> &historicWordRatePerCell,
	const WordToGridMap<double> &historicDeviationByCell,
	const Grid<int> &tweetCountPerCell);
