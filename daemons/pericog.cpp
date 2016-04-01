#include "pericog.h"

static const double EPS = 1;
static const int MIN_PTS = 3;

unsigned int last_runtime = 0, RECALL_SCOPE, PERIOD;

double WEST_BOUNDARY, EAST_BOUNDARY, NORTH_BOUNDARY, SOUTH_BOUNDARY;

const int THREAD_COUNT = 1;

sql::Connection* connection;
Tweet::Tweet(string time, string lat, string lon, string user, string _text)
{
	regex mentionsAndUrls("((\\B@)|(\\bhttps?:\\/\\/))[^\\s]+");
	regex nonWord("[^\\w]+");
	_text = regex_replace(_text, mentionsAndUrls, string(" "));
	_text = regex_replace(_text, nonWord, string(" "));

	id = time + "-" + user;
	time = stoi(time);
	lat = stod(lat);
	lon = stod(lon);
	text = explode(_text);
}

void compareTweets(const unique_ptr<Tweet> &a, const unique_ptr<Tweet> &b)
{
	double x_dist = (a->lat - b->lat);
	double y_dist = (a->lon - b->lon);
	double euclidean = sqrt(x_dist * x_dist + y_dist * y_dist);

	double similarity = 0;
	int repeats = 0;
	if (a->text.size() < b->text.size())
	{
		for (const auto &word : a->text)
		{
			if (b->text.count(word))
			{
				similarity += 1/a->text.size();
				repeats++;
			}
		}
	}
	else
	{
		for (const auto &word : b->text)
		{
			if (a->text.count(word))
			{
				similarity += 1/b->text.size();
				repeats++;
			}
		}
	}

	if (repeats)
	{
		double distance = (euclidean/repeats) - (similarity*similarity);
		if (distance < EPS)
		{
			a->neighbors.insert(make_pair(distance, b));
			b->neighbors.insert(make_pair(distance, a));
			a->require_core_distance_update = b->require_core_distance_update = true;
		}
	}
}

int main(int argc, char* argv[])
{
	TimeKeeper profiler;
	unordered_set<unique_ptr<Tweet>> tweets;
	profiler.start("Initialize");
	Initialize(argc, argv);

	while (1)
	{
		if (time(0) - last_runtime > PERIOD)
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
	assert(last_runtime != 0);

	// create a connection
	sql::Driver* driver(get_driver_instance());
	{
		ifstream passwordFile("/srv/etc/auth/daemons/pericog.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		connection = driver->connect("tcp://127.0.0.1:3306", "pericog", password);
	}
}

void updateTweets(unordered_set<unique_ptr<Tweet>> &tweets)
{
	// delete tweets too old to be related to new tweets
	for (const auto &tweet : tweets)
	{
		if (last_runtime - tweet->time > RECALL_SCOPE)
		{
			tweets.erase(tweet);
		}
	}

	unique_ptr<sql::ResultSet> dbTweets(connection->createStatement()->executeQuery(
		"SELECT *, UNIX_TIMESTAMP(time) as unix_time FROM NYC.tweets WHERE time BETWEEN FROM_UNIXTIME(" + to_string(last_runtime - PERIOD) + ") AND FROM_UNIXTIME(" + to_string(last_runtime) + ");")
		);

	while (dbTweets->next())
	{
		unique_ptr<Tweet> new_tweet(
			dbTweets->getString("unix_time"),
			dbTweets->getString("lat"),
			dbTweets->getString("lon"),
			dbTweets->getString("user"),
			dbTweets->getString("text")
			);

		for (const auto &tweet : tweets)
			compareTweets(new_tweet, tweet);

		tweets.insert(new_tweet);
	}

	// calculate core distances
	for (const auto &tweet : tweets)
	{
		if (tweet->require_core_distance_update)
		{
			if (tweet->neighbors.size() < MIN_PTS)
			{
				tweet->core_distance = -1;
				continue;
			}

			auto iterator = tweet->neighbors.begin();
			advance(iterator, MIN_PTS-1);
			tweet->core_distance = iterator->first;
			tweet->require_core_distance_update = false;
		}
	}

}

void updateLastRun()
{
	ofstream last_runtime_file("/srv/lastrun/pericog");
	last_runtime_file << last_runtime;
	last_runtime += PERIOD;
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
