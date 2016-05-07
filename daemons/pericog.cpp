#include "pericog.h"

#define MAX_DEGREES_LATITUDE 90
#define MAX_DEGREES_LONGITUDE 180

unsigned int last_runtime = 0, RECALL_SCOPE, PERIOD, MIN_PTS;
double EPSILON, REACHABILITY_THRESHOLD, MAX_SPACIAL_DISTANCE, CELL_SIZE;

sql::Connection* connection;

vector<vector<Cell>> Cell::cells;

Tweet::Tweet(string _time, string _lat, string _lon, string _text)
	: text(_text)
{
	regex mentionsAndUrls("((\\B@)|(\\bhttps?:\\/\\/))[^\\s]+");
	regex nonWord("[^\\w]+");
	_text = regex_replace(_text, mentionsAndUrls, string(" "));
	_text = regex_replace(_text, nonWord, string(" "));

	time = stoi(_time);
	lon = stod(_lon);
	lat = stod(_lat);
	x = floor((lon + MAX_DEGREES_LONGITUDE)/CELL_SIZE);
	y = floor((lat + MAX_DEGREES_LATITUDE)/CELL_SIZE);
	words = explode(_text);

	auto &tweet_cell = Cell::cells[x][y];

	unsigned int regional_tweet_count = 0;
	unordered_map<string, unsigned int> regional_word_counts;
	for (const auto &regional_cell : tweet_cell.region)
	{
		regional_tweet_count += regional_cell->tweet_count;
		for (const auto &word : words)
		{
			if (!regional_word_counts.count(word))
				regional_word_counts[word] = 0;

			if (regional_cell->tweets_by_word.count(word))
			{
				regional_word_counts[word] += regional_cell->tweets_by_word.at(word).size();
			}
		}
	}

	for (const auto &word : words)
	{
		if (regional_word_counts.count(word))
			regional_word_rates[word] = (double)regional_word_counts.at(word) / regional_tweet_count;
		else
			regional_word_rates[word] = 0;
	}

	for (const auto &word : words)
	{
		tweet_cell.tweets_by_word[word].insert(this);
	}
	tweet_cell.tweet_count++;
}

Tweet::~Tweet()
{
	auto &tweets_by_word = Cell::cells[x][y].tweets_by_word;
	for (const auto &word : words)
	{
		tweets_by_word[word].erase(this);
		if (tweets_by_word[word].empty())
			tweets_by_word.erase(word);
	}
	Cell::cells[x][y].tweet_count--;

	// remove neighbor references to the tweet we are deleting from all neighbors
	for (const auto &optics_neighbor_pair : optics_neighbors)
	{
		auto &optics_neighbor = *(optics_neighbor_pair.second);
		optics_neighbor.require_update = true;
		for (const auto &neighbor_pair_of_neighbor : optics_neighbor.optics_neighbors)
		{
			if (neighbor_pair_of_neighbor.second == this)
			{
				optics_neighbor.optics_neighbors.erase(neighbor_pair_of_neighbor.first);
			}
		}
	}
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
			profiler.start("updateTweets");
			updateTweets(tweets);
			profiler.start("getReachabilityPlot");
			auto reachability_plot = getReachabilityPlot(tweets);
			profiler.start("extractClusters");
			auto clusters = extractClusters(reachability_plot);
			profiler.start("updateLastRun");
			updateLastRun();
		}
		usleep(10);
	}
}

void Initialize(int argc, char* argv[])
{
	getArg(RECALL_SCOPE,           "timing", "history");
	getArg(PERIOD,                 "timing", "period");
	getArg(CELL_SIZE,              "grid",   "cell_size");
	getArg(EPSILON,                "optics", "epsilon");
	getArg(MIN_PTS,                "optics", "minimum_points");
	getArg(REACHABILITY_THRESHOLD, "optics", "reachability_threshold");
	getArg(MAX_SPACIAL_DISTANCE,   "optics", "regional_radius");

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

	// generate grid
	int x = 0, y;
	Cell::cells.resize((MAX_DEGREES_LONGITUDE*2)/CELL_SIZE);
	for (auto &column : Cell::cells)
	{
		y = 0;
		column.resize((MAX_DEGREES_LATITUDE*2)/CELL_SIZE);
		for (auto &cell : column)
		{
			cell.x = x;
			cell.y = y;
			y++;
		}
		x++;
	}

	// TODO: make this not square
	const auto RADIUS = MAX_SPACIAL_DISTANCE/CELL_SIZE;
	for (auto &column : Cell::cells)
	{
		for (auto &cell : column)
		{
			for (unsigned int i = floor(cell.x-RADIUS); i <= ceil(cell.x+RADIUS); i++)
			{
				for (unsigned int j = floor(cell.y-RADIUS); j <= ceil(cell.y+RADIUS); j++)
				{
					// regions end at the poles and the international date line
					if (i >= Cell::cells.size() || j >= Cell::cells[0].size())
						continue;

					cell.region.push_back(&(Cell::cells[i][j]));
				}
			}
		}
	}

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
	// delete tweets too old to be related to new tweets, and all references to them
	while (tweets.size())
	{
		Tweet* &tweet = tweets.at(0);

		// the first tweet in tweets is always the oldest, so if it isn't old enough to be deleted, neither are any of the others
		if (tweet->time - last_runtime > RECALL_SCOPE)
			break;

		delete tweet;
		tweets.pop_front();
	}

	unique_ptr<sql::ResultSet> dbTweets(connection->createStatement()->executeQuery(
		"SELECT *, UNIX_TIMESTAMP(time) AS unix_time FROM NYC.tweets WHERE time BETWEEN FROM_UNIXTIME(" + to_string(last_runtime - PERIOD) + ") AND FROM_UNIXTIME(" + to_string(last_runtime) + ") ORDER BY time ASC;")
		);


	while (dbTweets->next())
	{
		Tweet* new_tweet = new Tweet(
			dbTweets->getString("unix_time"),
			dbTweets->getString("lat"),
			dbTweets->getString("lon"),
			dbTweets->getString("text")
			);

		// remove tweets consisting only of stopwords or other ignored strings
		if (!new_tweet->words.size())
		{
			delete new_tweet;
			continue;
		}

		for (const auto &word : new_tweet->words)
		{
			for (const auto &cell : Cell::cells[new_tweet->x][new_tweet->y].region)
			{
				if (cell->tweets_by_word.count(word))
				{
					for (const auto &tweet : cell->tweets_by_word.at(word))
					{
						const double &optics_distance = getOpticsDistance(*new_tweet, *tweet);

						new_tweet->optics_distances[tweet] = tweet->optics_distances[new_tweet] = optics_distance;

						// add neighbor references between the new tweet and all its neighbors
						if (optics_distance <= EPSILON)
						{
							new_tweet->optics_neighbors.insert(make_pair(optics_distance, tweet));
							tweet->optics_neighbors.insert(make_pair(optics_distance, new_tweet));
							tweet->require_update = true;
						}
					}
				}
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
			if (tweet->optics_neighbors.size() < MIN_PTS)
			{
				tweet->core_distance = EPSILON + 1;
				continue;
			}

			auto iterator = tweet->optics_neighbors.begin();
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

			for (const auto &optics_neighbor_pair : tweet->optics_neighbors)
			{
				const auto &optics_neighbor = optics_neighbor_pair.second;

				// tweet cannot be directly density-reachable from a non-core object
				if (optics_neighbor->core_distance > EPSILON)
					continue;

				double reachability_distance;
				if (tweet->optics_distances.at(optics_neighbor) > optics_neighbor->core_distance)
					reachability_distance = tweet->optics_distances.at(optics_neighbor);
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
			if (smallest_value_of_smallest_reachability_distance >= tweet->smallest_reachability_distance)
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

			for (const auto &pair : tweet->optics_neighbors)
			{
				const auto &optics_neighbor = pair.second;
				if (!tweets_to_process.count(optics_neighbor))
					continue;
				nodes.push(make_pair(optics_neighbor->smallest_reachability_distance, optics_neighbor));
				tweets_to_process.erase(optics_neighbor);
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

// MUST be commutative, ie getDistance(a,b) == getDistance(b,a) for all tweets
// MUST NOT return a negative value
double getOpticsDistance(const Tweet &a, const Tweet &b)
{
	double similarity = 0;
	const double size = a.words.size() > b.words.size() ? a.words.size() : b.words.size();
	for (const auto &word : a.words)
	{
		if (b.words.count(word))
		{
			const double word_weight_a = 1 - a.regional_word_rates.at(word);
			const double word_weight_b = 1 - b.regional_word_rates.at(word);
			const double word_weight = word_weight_a > word_weight_b ? word_weight_a : word_weight_b;
			similarity += word_weight/size;
		}
	}

	if (!similarity)
		return EPSILON + 1;

	return 1-similarity;
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
