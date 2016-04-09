#include "pericog.h"
#define STOPWORDS {"the", "and", "amp", "of", "you", "i", "a"}

const double EPSILON = 1;
const int MIN_PTS = 3;
const double REACHABILITY_THRESHOLD = 1;

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
	for (const string &word : STOPWORDS)
		text.erase(word);
}

int main(int argc, char* argv[])
{
	TimeKeeper profiler;
	deque<Tweet*> tweets;
	profiler.start("Initialize");
	Initialize(argc, argv);

	while (1)
	{
		if (time(0) - last_runtime > PERIOD)
		{
			updateTweets(tweets);
			auto reachability_plot = getReachabilityPlot(tweets);
			auto clusters = extractClusters(reachability_plot);
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
		ifstream passwordFile("/srv/auth/daemons/pericog.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		connection = driver->connect("tcp://127.0.0.1:3306", "pericog", password);
	}
}

void updateTweets(deque<Tweet*> &tweets)
{
	// delete tweets too old to be related to new tweets
	while (last_runtime - tweets.at(0)->time > RECALL_SCOPE)
	{
		for (const auto &neighborPair : tweets.at(0)->neighbors)
		{
			neighborPair.second->require_update = true;
		}
		delete tweets.at(0);
		tweets.pop_front();
	}

	unique_ptr<sql::ResultSet> dbTweets(connection->createStatement()->executeQuery(
		"SELECT *, UNIX_TIMESTAMP(time) as unix_time FROM NYC.tweets WHERE time BETWEEN FROM_UNIXTIME(" + to_string(last_runtime - PERIOD) + ") AND FROM_UNIXTIME(" + to_string(last_runtime) + ") ORDER BY time ASC;")
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

		for (const auto &tweet : tweets)
		{
			double distance = getDistance(*new_tweet, *tweet);
			new_tweet->distances[tweet] = tweet->distances[new_tweet] = distance;
			if (distance <= EPSILON)
			{
				new_tweet->neighbors.insert(make_pair(distance, tweet));
				tweet->neighbors.insert(make_pair(distance, new_tweet));
				tweet->require_update = true;
			}
		}

		tweets.push_back(new_tweet);
	}

	tweets.shrink_to_fit();

	// calculate core distances
	for (const auto &tweet : tweets)
	{
		if (tweet->require_update)
		{
			// non-core objects (borders and noise) are denoted by a core distance greater than epsilon
			if (tweet->neighbors.size() < MIN_PTS)
			{
				tweet->core_distance = EPSILON + 1;
				continue;
			}

			auto iterator = tweet->neighbors.begin();
			advance(iterator, MIN_PTS-1);
			tweet->core_distance = iterator->first;
		}
	}

	// calculate smallest reachability distances
	for (const auto &tweet : tweets)
	{
		if (tweet->require_update)
		{
			// noise is denoted by a smallest reachability distance greater than epsilon
			tweet->smallest_reachability_distance = EPSILON + 1;

			for (const auto &neighborPair : tweet->neighbors)
			{
				const auto &neighbor = neighborPair.second;
				// tweet cannot be directly density-reachable from a non-core object
				if (neighbor->core_distance > EPSILON)
					continue;

				double reachability_distance;
				if (tweet->distances.at(neighbor) > neighbor->core_distance)
					reachability_distance = tweet->distances.at(neighbor);
				else
					reachability_distance = tweet->core_distance;

				if (tweet->smallest_reachability_distance > reachability_distance)
					tweet->smallest_reachability_distance = reachability_distance;
			}

			tweet->require_update = false;
		}
	}
}

vector<Tweet*> getReachabilityPlot(const deque<Tweet*> &tweets)
{
	// construct a container of all non-noise tweets for processing
	unordered_set<Tweet*> tweets_to_process;
	for (const auto &tweet : tweets)
	{
		if (tweet->smallest_reachability_distance > EPSILON)
			continue;
		tweets_to_process.insert(tweet);
	}

	vector<Tweet*> reachability_plot;
	reachability_plot.reserve(tweets_to_process.size());

	priority_queue<pair<double, Tweet*>, deque<pair<double, Tweet*>>> nodes;

	while (!tweets_to_process.empty())
	{
		// branch from an unprocessed core object with the smallest value of its smallest reachability distance
		// this node is not special, but it is likely to be in the most dense tweet region
		// this selectivity also makes the algorithm more deterministic, though not perfectly
		double smallest_value_of_smallest_reachability_distance = EPSILON + 1;
		Tweet* seed;
		for (const auto &tweet : tweets_to_process)
		{
			// exclude border objects
			if (tweet->core_distance > EPSILON)
				continue;

			if (smallest_value_of_smallest_reachability_distance > tweet->smallest_reachability_distance)
			{
				smallest_value_of_smallest_reachability_distance = tweet->smallest_reachability_distance;
				seed = tweet;
			}

		}
		nodes.push(make_pair(0, seed));
		tweets_to_process.erase(seed);

		// process the tree of nodes connected to the seed node in order of reachability
		while (!nodes.empty())
		{
			auto &tweet = nodes.top().second;
			nodes.pop();
			reachability_plot.push_back(tweet);

			// acquire, but do not branch through border objects
			if (tweet->core_distance > EPSILON)
				continue;

			for (const auto &pair : tweet->neighbors)
			{
				const auto &neighbor = pair.second;
				if (!tweets_to_process.count(neighbor))
					continue;
				nodes.push(make_pair(neighbor->smallest_reachability_distance, neighbor));
				tweets_to_process.erase(neighbor);
			}
		}
	}
	return reachability_plot;
}

vector<vector<Tweet*>> extractClusters(vector<Tweet*> reachability_plot)
{
	vector<vector<Tweet*>> clusters;
	bool in_cluster = false;
	vector<Tweet*>::iterator cluster_start;
	for (auto i = reachability_plot.begin(); i != reachability_plot.end(); i++)
	{
		if (!in_cluster && (*i)->smallest_reachability_distance <= REACHABILITY_THRESHOLD)
		{
			cluster_start = i;
			in_cluster = true;
		}
		else if (in_cluster && (*i)-> smallest_reachability_distance > REACHABILITY_THRESHOLD)
		{
			vector<Tweet*> cluster(cluster_start, i-1);
			clusters.push_back(cluster);
			in_cluster = false;
		}
	}
	return clusters;
}

// this function MUST be commutative, ie getDistance(a,b) == getDistance(b,a) for all tweets
double getDistance(const Tweet &a, const Tweet &b)
{
	double x_dist = (a.lat - b.lat);
	double y_dist = (a.lon - b.lon);
	double euclidean = sqrt(x_dist * x_dist + y_dist * y_dist);

	double similarity = 0;
	int repeats = 0;
	if (a.text.size() < b.text.size())
	{
		for (const auto &word : a.text)
		{
			if (b.text.count(word))
			{
				similarity += 1/a.text.size();
				repeats++;
			}
		}
	}
	else
	{
		for (const auto &word : b.text)
		{
			if (a.text.count(word))
			{
				similarity += 1/b.text.size();
				repeats++;
			}
		}
	}

	if (repeats)
		return (euclidean/repeats) - (similarity*similarity);
	else
		return EPSILON + 1;
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
