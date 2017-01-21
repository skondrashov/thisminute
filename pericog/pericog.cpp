#include "pericog.h"

const int
	MAX_DEGREES_LATITUDE = 90,
	MAX_DEGREES_LONGITUDE = 180;

unsigned int last_runtime = 0, RECALL_SCOPE, PERIOD, MIN_PTS, MIN_TWEETS = 3, VECTOR_SIZE;
double EPSILON, REACHABILITY_MAXIMUM, REACHABILITY_MINIMUM, MAX_SPACIAL_DISTANCE, CELL_SIZE;
string ACTIVE_ZONE, TARGET_IP;

sql::Connection* admin_connection, * limited_connection;

vector<vector<Cell>> Cell::cells;
Tweet* Tweet::delimiter;

Tweet::Tweet(string _time, string _lat, string _lon, string _text, string _user, string _exact, vector<double> _feature_vector)
	: text(_text), feature_vector(_feature_vector)
{
	static regex mentionsAndUrls("((\\B@)|(\\bhttps?:\\/\\/))[^\\s]+");
	static regex nonWord("[^\\w]+");

	_text = regex_replace(_text, mentionsAndUrls, string(" "));
	_text = regex_replace(_text, nonWord, string(" "));
	transform(_text.begin(), _text.end(), _text.begin(), ::tolower);
	_text.erase(0, _text.find_first_not_of(" "));
	_text.erase(_text.find_last_not_of(" ") + 1);
	clean_text = _text;

	time = stoi(_time);
	lon = stod(_lon);
	lat = stod(_lat);
	x = floor((lon + MAX_DEGREES_LONGITUDE)/CELL_SIZE);
	y = floor((lat + MAX_DEGREES_LATITUDE)/CELL_SIZE);
	words = explode(clean_text);
	user = _user;
	exact = (bool)stoi(_exact);

	auto &tweet_cell = Cell::cells[x][y];

	// update cell
	tweet_cell.tweet_count++;
	for (const auto &word : words)
	{
		tweet_cell.tweets_by_word[word].insert(this);
	}

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
		if (regional_word_counts.count(word) && regional_tweet_count)
			regional_word_rates[word] = (double)regional_word_counts.at(word) / regional_tweet_count;
		else
			regional_word_rates[word] = 0;
	}
}

Tweet::~Tweet()
{
	// undo changes to cell
	auto &tweets_by_word = Cell::cells[x][y].tweets_by_word;
	for (const auto &word : words)
	{
		tweets_by_word[word].erase(this);
		if (tweets_by_word[word].empty())
			tweets_by_word.erase(word);
	}

	// remove neighbor references to the tweet we are deleting from all neighbors
	for (const auto &optics_neighbor_pair : optics_neighbors)
	{
		auto &optics_neighbor = *(optics_neighbor_pair.second);
		optics_neighbor.require_update = true;
		for (const auto &neighbor_pair_of_neighbor : optics_neighbor.optics_neighbors)
		{
			if (neighbor_pair_of_neighbor.second == this)
			{
				// we have to make sure we don't accidentally delete different pairs with identical keys (possible in multimap)
				// (C) guy on S/O: http://stackoverflow.com/questions/3952476/how-to-remove-a-specific-pair-from-a-c-multimap
				typedef multimap<double, Tweet*>::iterator iterator;
				std::pair<iterator, iterator> iterpair = optics_neighbor.optics_neighbors.equal_range(neighbor_pair_of_neighbor.first);
				for (iterator it = iterpair.first; it != iterpair.second; ++it)
				{
					if (it->second == this)
					{
						optics_neighbor.optics_neighbors.erase(it);
						break;
					}
				}
			}
		}
	}
}

int main()
{
	TimeKeeper profiler;
	deque<Tweet*> tweets;

	profiler.start("Initialize");
	Initialize();

	while (1)
	{
		if (time(0) - last_runtime > PERIOD)
		{
			profiler.start("updateTweets");
			updateTweets(tweets);
			profiler.start("getClusters");
			auto clusters = getClusters(tweets);
			profiler.start("filterClusters");
			filterClusters(clusters);
			profiler.start("writeClusters");
			writeClusters(clusters);
			profiler.start("updateLastRun");
			updateLastRun();
			profiler.stop();
			cout << "Tweets: " << tweets.size() << endl;
			cout << "Time: " << last_runtime << endl;
		}
		usleep(10);
	}
}

void Initialize()
{
	getArg(RECALL_SCOPE,         "timing",      "history");
	getArg(PERIOD,               "timing",      "period");
	getArg(last_runtime,         "timing",      "start");
	getArg(CELL_SIZE,            "grid",        "cell_size");
	getArg(MAX_SPACIAL_DISTANCE, "grid",        "regional_radius");
	getArg(EPSILON,              "optics",      "epsilon");
	getArg(MIN_PTS,              "optics",      "minimum_points");
	getArg(REACHABILITY_MAXIMUM, "optics",      "reachability_max");
	getArg(REACHABILITY_MINIMUM, "optics",      "reachability_min");
	getArg(ACTIVE_ZONE,          "connections", "active");
	getArg(TARGET_IP,            "connections", ACTIVE_ZONE);
	getArg(VECTOR_SIZE,          "tweet2vec",   "vector_size");

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

	vector<double> temp;
	Tweet::delimiter = new Tweet(0, 0.0, 0.0, "DELIMIT", "0", false, temp);
	Tweet::delimiter->smallest_reachability_distance = REACHABILITY_MAXIMUM + 1;

	// TODO: make this not square
	const auto RADIUS = MAX_SPACIAL_DISTANCE/CELL_SIZE;
	for (auto &column : Cell::cells)
	{
		for (auto &cell : column)
		{
			for (auto i = floor(cell.x-RADIUS); i <= ceil(cell.x+RADIUS); i++)
			{
				for (auto j = floor(cell.y-RADIUS); j <= ceil(cell.y+RADIUS); j++)
				{
					// regions end at the poles and the international date line
					if (i >= Cell::cells.size() || j >= Cell::cells[0].size())
						continue;

					cell.region.push_back(&(Cell::cells[i][j]));
				}
			}
		}
	}

	// create a connection with limited permissions - relatively safe in the event of SQL injection
	{
		sql::Driver* driver(get_driver_instance());
		ifstream passwordFile("/srv/auth/daemons/pericog_limited.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		limited_connection = driver->connect("tcp://" +TARGET_IP+ ":3306", "pericog_limited", password);
		limited_connection->setSchema("ThisMinute");
	}

	// create a connection that will only perform queries that are not constructed from user input
	{
		sql::Driver* driver(get_driver_instance());
		ifstream passwordFile("/srv/auth/daemons/pericog_admin.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		admin_connection = driver->connect("tcp://" +TARGET_IP+ ":3306", "pericog_admin", password);
		admin_connection->setSchema("ThisMinute");
	}
}

void updateTweets(deque<Tweet*> &tweets)
{
	// insert new tweets into tweet_vector table for processing
	admin_connection->createStatement()->execute(
			"INSERT INTO tweet_vectors (`tweet_id`) SELECT id FROM tweets WHERE time BETWEEN FROM_UNIXTIME("
				+to_string(last_runtime - PERIOD)+ ") AND FROM_UNIXTIME(" +to_string(last_runtime)+ ")"
		);

	// delete tweets too old to be related to new tweets, and all references to them
	while (tweets.size())
	{
		Tweet* &tweet = tweets.at(0);

		// the first tweet in tweets is always the oldest, so if it isn't old enough to be deleted, neither are any of the others
		if (last_runtime - tweet->time < RECALL_SCOPE)
			break;

		delete tweets.at(0);
		tweets.pop_front();
	}

	while (true)
	{
		usleep(100);
		unique_ptr<sql::ResultSet> db_tweets(admin_connection->createStatement()->executeQuery(
				"SELECT *, UNIX_TIMESTAMP(time) AS unix_time FROM tweet_vectors "
				"JOIN tweets ON tweet_vectors.tweet_id = tweets.id "
				"WHERE status = 1"
			));

		while (db_tweets->next())
		{
			admin_connection->createStatement()->execute(
					"UPDATE tweet_vectors SET status = 2 WHERE tweet_id = " + db_tweets->getString("id")
				);

			vector<double> tweet_feature_vector;
			tweet_feature_vector.reserve(VECTOR_SIZE);
			for (unsigned int i=0; i<VECTOR_SIZE; ++i)
			{
				tweet_feature_vector.push_back(stod(db_tweets->getString("v" + to_string(i))));
			}

			Tweet* new_tweet = new Tweet(
					db_tweets->getString("unix_time"),
					db_tweets->getString("lat"),
					db_tweets->getString("lon"),
					db_tweets->getString("text"),
					db_tweets->getString("user"),
					db_tweets->getString("exact"),
					tweet_feature_vector
				);

			// ignore tweets consisting only of stopwords or other ignored strings
			if (!new_tweet->words.size())
			{
				delete new_tweet;
				continue;
			}

			for (const auto &word : new_tweet->words)
			{
				for (const auto &cell : Cell::cells[new_tweet->x][new_tweet->y].region)
				{
					if (!(cell->tweets_by_word.count(word)))
						continue;

					for (const auto &tweet : cell->tweets_by_word.at(word))
					{
						if (tweet == new_tweet || new_tweet->optics_distances.count(tweet))
							continue;

						const double &optics_distance = getDistance(tweet->feature_vector, new_tweet->feature_vector);

						if (optics_distance < 0.3 && optics_distance > .0001)
							cout << tweet->text << "\n" << new_tweet->text << "\n" << optics_distance << "\n\n";

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

			tweets.push_back(new_tweet);
		}

		unique_ptr<sql::ResultSet> db_continue(admin_connection->createStatement()->executeQuery(
				"SELECT COUNT(*) AS pending FROM tweet_vectors WHERE status != 2"
			));
		db_continue->next();
		if (!stoi(db_continue->getString("pending")))
			break;
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

vector<vector<Tweet*>> getClusters(const deque<Tweet*> &tweets)
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
		reachability_plot.push_back(Tweet::delimiter);

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

	vector<vector<Tweet*>> clusters;
	bool in_cluster = false;
	vector<Tweet*>::iterator cluster_start;
	for (auto i = reachability_plot.begin(); i != reachability_plot.end(); i++)
	{
		if (!in_cluster && (*i)->smallest_reachability_distance <= REACHABILITY_MAXIMUM
			&& (*i)->smallest_reachability_distance >= REACHABILITY_MINIMUM
			)
		{
			cluster_start = i;
			in_cluster = true;
		}
		else if (in_cluster && (((*i)->smallest_reachability_distance > REACHABILITY_MAXIMUM)
			|| ((*i)->smallest_reachability_distance < REACHABILITY_MINIMUM)))
		{
			vector<Tweet*> cluster(cluster_start, i);
			in_cluster = false;
			if (cluster.size() > MIN_TWEETS)
			{
				const string &first_user = cluster[0]->user;
				for (const auto &tweet : cluster)
				{
					if (tweet->user != first_user)
					{
						clusters.push_back(cluster);
						break;
					}
				}
			}
		}
	}

	return clusters;
}

void filterClusters(vector<vector<Tweet*>> &clusters)
{

}

void writeClusters(vector<vector<Tweet*>> &clusters)
{
	if (clusters.empty())
		return;

	admin_connection->createStatement()->execute("DROP TABLE IF EXISTS events_new, event_tweets_new");
	admin_connection->createStatement()->execute("CREATE TABLE events_new LIKE events");
	admin_connection->createStatement()->execute("CREATE TABLE event_tweets_new LIKE event_tweets");

	// each cluster is an event containing time and location information as well as an id to access all of its child tweets
	int i = 0;
	for (const auto &cluster : clusters)
	{
		double avgX, avgY;
		avgX = avgY = 0.0;
		unsigned int start_time, end_time;
		start_time = end_time = cluster[0]->time;
		unordered_set<string> users;
		for (const auto &tweet : cluster)
		{
			avgX += tweet->lon;
			avgY += tweet->lat;
			if (tweet->time < start_time)
				start_time = tweet->time;
			if (tweet->time > end_time)
				end_time = tweet->time;
			users.insert(tweet->user);
		}
		avgX /= cluster.size();
		avgY /= cluster.size();

		admin_connection->createStatement()->execute(
			"INSERT INTO events_new (`id`, `lon`, `lat`, `start_time`, `end_time`, `users`) VALUES ("
					+to_string(i)+ ","
					+to_string(avgX)+ ","
					+to_string(avgY)+ ","
					"FROM_UNIXTIME(" +to_string(start_time)+ "),"
					"FROM_UNIXTIME(" +to_string(end_time)+ "),"
					+to_string(users.size())+
				")");

		string query = "INSERT INTO event_tweets_new (`event_id`, `time`, `lat`, `lon`, `exact`, `text`) VALUES ";
		for (const auto &tweet : cluster)
		{
			string escaped_tweet_text = tweet->text;
			size_t pos;
			while ((pos = escaped_tweet_text.find("'")) != string::npos)
			{
				escaped_tweet_text.replace(pos, 0, "''");
			}

			query +=
				"( "
					+to_string(i)+ ","
					"FROM_UNIXTIME(" +to_string(tweet->time)+ "),"
					+to_string(avgX)+ ","
					+to_string(avgY)+ ","
					+to_string(tweet->exact)+ ","
					"'" +escaped_tweet_text+ "'"
				"),";
		}
		query.pop_back(); // take the extra comma out
		limited_connection->createStatement()->execute(query);

		i++;
	}

	admin_connection->createStatement()->execute("DROP TABLE IF EXISTS events_old, event_tweets_old");
	admin_connection->createStatement()->execute(
			"RENAME TABLE "
				"events TO events_old,"
				"event_tweets TO event_tweets_old,"
				"events_new TO events,"
				"event_tweets_new TO event_tweets"
		);
}

double getDistance(const vector<double> &A, const vector<double> &B)
{
	double dot = 0.0, denom_a = 0.0, denom_b = 0.0 ;
	for (auto i = 0u; i < VECTOR_SIZE; ++i)
	{
		dot += A[i] * B[i] ;
		denom_a += A[i] * A[i] ;
		denom_b += B[i] * B[i] ;
	}
	return 1 - (dot / (sqrt(denom_a) * sqrt(denom_b))) ;
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
		if (token != "" && token != " ")
			result.insert(token);
	}

	return result;
}

string getArg(string section, string option)
{
	static INIReader reader("/srv/config.ini");
	static string errorValue = "INI_READ_ERROR";
	string arg = reader.Get(section, option, errorValue);
	assert(arg != errorValue);
	return arg;
}

void getArg(unsigned int &arg, string section, string option)
{
	arg = stoi(getArg(section, option));
}

void getArg(double &arg, string section, string option)
{
	arg = stod(getArg(section, option));
}

void getArg(string &arg, string section, string option)
{
	arg = getArg(section, option);
}
