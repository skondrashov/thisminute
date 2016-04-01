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
	static const double EPS = 1;
	static const int MIN_PTS = 3;

	bool processed = false;
	bool require_core_distance_update = true;
	double core_distance;

	double lat, lon;
	unsigned int time;
	unordered_set<string> text;
	string id;
	multimap<double, Tweet*> neighbors;
	unordered_map<Tweet*, double> distances;

	Tweet(string time, string lat, string lon, string user, string text) {
		static const regex mentionsAndUrls("((\\B@)|(\\bhttps?:\\/\\/))[^\\s]+");
		static const regex nonWord("[^\\w]+");
		text = regex_replace(text, mentionsAndUrls, string(" "));
		text = regex_replace(text, nonWord, string(" "));

		id = time + "-" + user;
		time = stoi(time);
		lat = stod(lat);
		lon = stod(lon);
		text = explode(text);
	}

	void compare(Tweet &other) {
		double x_dist = (lat - other.lat);
		double y_dist = (lon - other.lon);
		double euclidean = sqrt(x_dist * x_dist + y_dist * y_dist);

		double similarity = 0;
		int repeats = 0;
		if (text.size() < other.text.size())
		{
			for (const auto &word : text)
			{
				if (other.text.count(word))
				{
					similarity += 1/text.size();
					repeats++;
				}
			}
		}
		else
		{
			for (const auto &word : other.text)
			{
				if (text.count(word))
				{
					similarity += 1/other.text.size();
					repeats++;
				}
			}
		}

		if (repeats)
		{
			double distance = (euclidean/repeats) - (similarity*similarity);
			if (distance < Tweet.EPS)
			{
				neighbors.insert(make_pair(distance, &other));
				other.neighbors.insert(make_pair(distance, this));
				require_core_distance_update = other.require_core_distance_update = true;
			}
		}
	}
};

// utility functions
unordered_set<string> explode(string const &s);
template<typename T> void getArg(T &arg, string section, string option);

// YEAH LET'S DO IT
void Initialize(int argc, char* argv[]);
void updateTweets(unordered_map<string, Tweet> &tweets);
void updateLastRun();
void OPTICS();