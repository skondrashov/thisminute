#include "pericog.h"

int last_runtime = -1, RECALL_SCOPE, PERIOD;

double WEST_BOUNDARY, EAST_BOUNDARY, NORTH_BOUNDARY, SOUTH_BOUNDARY;

const int THREAD_COUNT = 1;

sql::Connection* connection;
ofstream verboseOutputFile;
string verboseOutputFileName;

int main(int argc, char* argv[])
{
	TimeKeeper profiler;
	unordered_set<Tweet*> tweets;
	profiler.start("Initialize");
	Initialize(argc, argv);

	while (1)
	{
		if (time() - last_runtime > PERIOD)
		{
			updateTweets(tweets);
			updateLastRun();
		}
	}
}

void Initialize(int argc, char* argv[])
{
	getArg(RECALL_SCOPE,                  "timing",    "history");
	getArg(PERIOD,                        "timing",    "period");
	getArg(WEST_BOUNDARY,                 "grid",      "west");
	getArg(EAST_BOUNDARY,                 "grid",      "east");
	getArg(SOUTH_BOUNDARY,                "grid",      "south");
	getArg(NORTH_BOUNDARY,                "grid",      "north");

	char tmp;
	while ((tmp = getopt(argc, argv, "l:cov:1:2:3:4:")) != -1)
	{
		switch (tmp)
		{
		case 'l':
			last_runtime = stoi(optarg);
			break;
		}
	}
	assert(last_runtime != -1);

	// create a connection
	sql::Driver* driver(get_driver_instance());
	{
		ifstream passwordFile("/srv/etc/auth/daemons/pericog.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		connection = driver->connect("tcp://127.0.0.1:3306", "pericog", password);
	}
}

void updateTweets(unordered_map<string, Tweet> tweets)
{
	// delete tweets too old to be related to new tweets
	for (const auto &pair : tweets)
	{
		if (last_runtime - pair.second->time > RECALL_SCOPE)
		{
			tweets.erase(pair.first);
		}
	}

	unique_ptr<sql::ResultSet> dbTweets(connection->createStatement()->executeQuery(
		"SELECT *, UNIX_TIMESTAMP(time) as unix_time FROM NYC.tweets WHERE time BETWEEN FROM_UNIXTIME(" + to_string(LOOKBACK_TIME - PERIOD) + ") AND FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ");")
		);

	while (dbTweets->next())
	{
		Tweet* new_tweet = new Tweet(
			dbTweets->getString("unix_time"),
			dbTweets->getString("lat"),
			dbTweets->getString("lon"),
			dbTweets->getString("user"),
			dbTweets->getString("text")
			);

		for (const auto &pair : tweets)
			new_tweet->compare(*(pair.second));

		tweets.insert(new_tweet);
	}

	// calculate core distances
	for (const auto &pair : tweets)
	{
		const auto &tweet = *(pair.second);
		if (tweet.require_core_distance_update)
		{
			if (tweet.neighbors.size() < MIN_PTS)
			{
				tweet.core_distance = -1;
				continue;
			}

			auto iterator = tweet.neighbors.begin();
			advance(iterator, MIN_PTS-1);
			tweet.core_distance = iterator->first;
			tweet.require_core_distance_update = false;
		}
	}

}

void updateLastRun()
{
	ofstream last_runtime_file("/srv/lastrun/pericog");
	last_runtime_file << last_runtime;
	last_runtime += PERIOD;
}

vector<double> OPTICS()
{
	vector<Tweet*> ordered_list;
	for (const auto &pair : tweets)
	{
		if (pair.second->processed)
			continue;
		pair.second->processed = true;
		ordered_list.push_back(pair.first);
	}
}

unordered_set<string> explode(string const &s)
{
	unordered_set<string> result;
	istringstream iss(s);

	for (string token; getline(iss, token, ' '); )
	{
		transform(token.begin(), token.end(), token.begin(), ::tolower);
		if (token != "" && token != " ")
			result.insert(token);
	}

	return result;
}

template<typename T> void getArg(T &arg, string section, string option)
{
	static INIReader reader("/srv/etc/config/daemons.ini");
	static double errorValue = -9999;
	arg = (T)reader.GetReal(section, option, errorValue);
	assert(arg != errorValue);
}
