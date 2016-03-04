#include "pericog.h"

int LOOKBACK_TIME = -1, RECALL_SCOPE, PERIOD, PERIODS_IN_HISTORY;
int MAP_HEIGHT, MAP_WIDTH;
bool SCAN_EVENTS = false, VERBOSE_OUTPUT = false, USE_CACHE = false;

double WEST_BOUNDARY, EAST_BOUNDARY, NORTH_BOUNDARY, SOUTH_BOUNDARY, RESOLUTION, SPACIAL_PERCENTAGE_THRESHOLD, TEMPORAL_PERCENTAGE_THRESHOLD, SPACIAL_DEVIATIONS_THRESHOLD, TEMPORAL_DEVIATIONS_THRESHOLD;

const int THREAD_COUNT = 2;

sql::Connection* connection;
ofstream verboseOutputFile;
string verboseOutputFileName;

int main(int argc, char* argv[])
{
	Stats stats;
	TimeKeeper profiler;

	profiler.start("Initialize");
	Initialize(argc, argv);

	if (!USE_CACHE || !readCache(stats))
	{
		// save all tweets since the specified time to an array
		profiler.start("getUserIdToTweetMap");
		auto userIdToTweetMap = getUserIdToTweetMap();

		profiler.start("refineTweetsAndGetTweetCountPerCell");
		stats.tweetCounts = refineTweetsAndGetTweetCountPerCell(userIdToTweetMap);

		profiler.start("getCurrentWordCountPerCell");
		getCurrentWordCountPerCell(stats, userIdToTweetMap);

		profiler.start("getCurrentLocalAndGlobalRatesForWord");
		getCurrentLocalAndGlobalRatesForWord(stats);

		// profiler.start("getHistoricWordRatesAndDeviation");
		// getHistoricWordRatesAndDeviation(stats);

		profiler.start("commitRates");
		commitStats(stats);
	}

	profiler.start("detectEvents");
	if (SCAN_EVENTS)
		detectEvents(stats);

	profiler.stop();
	return 0;
}

void Initialize(int argc, char* argv[])
{
	getArg(RECALL_SCOPE,                  "timing",    "history");
	getArg(PERIOD,                        "timing",    "period");
	getArg(WEST_BOUNDARY,                 "grid",      "west");
	getArg(EAST_BOUNDARY,                 "grid",      "east");
	getArg(SOUTH_BOUNDARY,                "grid",      "south");
	getArg(NORTH_BOUNDARY,                "grid",      "north");
	getArg(RESOLUTION,                    "grid",      "cell_size");
	getArg(SPACIAL_PERCENTAGE_THRESHOLD,  "threshold", "spacial_percentage");
	getArg(TEMPORAL_PERCENTAGE_THRESHOLD, "threshold", "temporal_percentage");
	getArg(SPACIAL_DEVIATIONS_THRESHOLD,  "threshold", "spacial_deviations");
	getArg(TEMPORAL_DEVIATIONS_THRESHOLD, "threshold", "temporal_deviations");

	char tmp;
	while ((tmp = getopt(argc, argv, "l:cov:1:2:3:4:")) != -1)
	{
		switch (tmp)
		{
		case 'l':
			LOOKBACK_TIME = stoi(optarg);
			break;
		case 'o':
			SCAN_EVENTS = true;
			break;
		case 'c':
			USE_CACHE = true;
			break;
		case 'v':
			VERBOSE_OUTPUT = true;
			verboseOutputFileName = optarg;
			break;
		case '1':
			SPACIAL_PERCENTAGE_THRESHOLD = stod(optarg);
			break;
		case '2':
			TEMPORAL_PERCENTAGE_THRESHOLD = stod(optarg);
			break;
		case '3':
			SPACIAL_DEVIATIONS_THRESHOLD = stod(optarg);
			break;
		case '4':
			TEMPORAL_DEVIATIONS_THRESHOLD = stod(optarg);
			break;
		}
	}
	assert(LOOKBACK_TIME != -1);

	MAP_WIDTH = static_cast<int>(round(abs((WEST_BOUNDARY - EAST_BOUNDARY) / RESOLUTION)));
	MAP_HEIGHT = static_cast<int>(round(abs((SOUTH_BOUNDARY - NORTH_BOUNDARY) / RESOLUTION)));
	PERIODS_IN_HISTORY = RECALL_SCOPE / PERIOD;

	// create a connection
	sql::Driver* driver(get_driver_instance());
	{
		ifstream passwordFile("/srv/etc/auth/daemons/pericog.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		connection = driver->connect("tcp://127.0.0.1:3306", "pericog", password);
	}
}

bool readCache(Stats &stats)
{
	unique_ptr<sql::ResultSet> dbStats(connection->createStatement()->executeQuery(
		"SELECT * FROM NYC.stat_cache WHERE time = FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ");"
		));

	// no cache found
	if (dbStats->rowsCount() == 0)
		return false;

	while (dbStats->next())
	{
		const auto &word = dbStats->getString("word");
		const auto &x = stoi(dbStats->getString("x"));
		const auto &y = stoi(dbStats->getString("y"));

		stats.perWord[word].currentCounts[x][y]      = stoi(dbStats->getString("count"));
		stats.perWord[word].currentRates[x][y]       = stod(dbStats->getString("rate"));
		stats.perWord[word].historicMeanRates[x][y]  = stod(dbStats->getString("historic_mean"));
		stats.perWord[word].historicDeviations[x][y] = stod(dbStats->getString("historic_deviation"));

		// this tweet count should be accurate for any cell no matter what word we're using. can use this for sanity checks
		if (stats.tweetCounts[x][y] == 0 && stats.perWord[word].currentCounts[x][y] > 0)
			stats.tweetCounts[x][y] = stats.perWord[word].currentCounts[x][y] / stats.perWord[word].currentRates[x][y];
	}

	return true;
}

unordered_map<int, Tweet> getUserIdToTweetMap()
{
	unordered_map<int, Tweet> tweets;

	unique_ptr<sql::ResultSet> dbTweets(connection->createStatement()->executeQuery(
		"SELECT * FROM NYC.tweets WHERE time BETWEEN FROM_UNIXTIME(" + to_string(LOOKBACK_TIME - PERIOD) + ") AND FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ");")
		);

	while (dbTweets->next())
	{
		const double lon = stod(dbTweets->getString("lon"));
		const double lat = stod(dbTweets->getString("lat"));

		// if a tweet is located outside of the grid, ignore it and go to the next tweet
		if (lon < WEST_BOUNDARY || lon > EAST_BOUNDARY
			|| lat < SOUTH_BOUNDARY || lat > NORTH_BOUNDARY)
			continue;

		int userId = stoi(dbTweets->getString("user"));

		auto tweetIter = tweets.find(userId);
		if (tweetIter == tweets.end())
		{
			const int
				x = floor((lon - WEST_BOUNDARY) / RESOLUTION),
				y = floor((lat - SOUTH_BOUNDARY) / RESOLUTION);

			Tweet tweet(x, y, dbTweets->getString("text"));

			tweets.insert({ userId, tweet });
		}
		else
		{
			tweetIter->second.text += " " + dbTweets->getString("text");
		}
	}

	return tweets;
}

// refine each tweet into usable information
Grid<int> refineTweetsAndGetTweetCountPerCell(unordered_map<int, Tweet> &userIdTweetMap)
{
	auto tweetsPerCell = makeGrid<int>();

	queue<Tweet*> tweetQueue;
	for (auto &pair : userIdTweetMap)
		tweetQueue.push(&pair.second);

	mutex tweetQueueLock;
	mutex tweetsPerCellLock;

	auto processTweets = [&]()
		{
			while (true)
			{
				tweetQueueLock.lock();
				if (tweetQueue.empty())
				{
					tweetQueueLock.unlock();
					return;
				}
				Tweet &tweet = *tweetQueue.front();
				tweetQueue.pop();
				tweetQueueLock.unlock();

				// remove mentions and URLs
				regex mentionsAndUrls("((\\B@)|(\\bhttps?:\\/\\/))[^\\s]+");
				tweet.text = regex_replace(tweet.text, mentionsAndUrls, string(" "));

				// remove all non-word characters
				regex nonWord("[^\\w]+");
				tweet.text = regex_replace(tweet.text, nonWord, string(" "));

				tweetsPerCellLock.lock();
				tweetsPerCell[tweet.x][tweet.y]++;
				tweetsPerCellLock.unlock();
			}
		};

	vector<thread> threads;
	for (int i = 0; i < THREAD_COUNT; i++)
		threads.emplace_back(processTweets);

	for (int i = 0; i < THREAD_COUNT; i++)
		threads[i].join();

	return move(tweetsPerCell);
}

// refine each tweet into usable information
void getCurrentWordCountPerCell(Stats &stats, const unordered_map<int, Tweet> &userIdTweetMap)
{
	static const int DISCARD_WORDS_WITH_LESS_COUNT = 2; // discard words counted < 2 times

	unordered_map<string, int> wordCount;

	for (const auto &pair : userIdTweetMap)
	{
		auto tweet = pair.second;

		auto words = explode(tweet.text);
		for (const auto &word : words)
		{
			stats.perWord[word].currentCounts[tweet.x][tweet.y]++;
			wordCount[word]++;
		}
	}

	// the '&' character is interpreted as the word "amp"... squelch for now
	stats.perWord.erase("amp");

	// the word ' ' shows up sometimes... squelch for now
	stats.perWord.erase(" ");

	for (const auto& wordCountPair : wordCount)
	{
		if (wordCountPair.second < DISCARD_WORDS_WITH_LESS_COUNT)
			stats.perWord.erase(wordCountPair.first);
	}
}

// pair<WordToGridMap<double>, WordToGridMap<double>> getHistoricWordRatesAndDeviation()
// {
// 	WordToGridMap<double> historicWordRates, historicDeviations;

// 	TimeKeeper profiler;
// 	profiler.start("getHistoricWordRatesAndDeviation query");
// 	unique_ptr<sql::ResultSet> dbWordRates(connection->createStatement()->executeQuery(
// 		"SELECT * FROM NYC.rates WHERE time BETWEEN FROM_UNIXTIME(" +
// 		to_string(LOOKBACK_TIME - RECALL_SCOPE) + ") AND FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ");"
// 		));

// 	unordered_map<string, vector<Grid<double>>> rates;

// 	profiler.start("getHistoricWordRatesAndDeviation getrates");
// 	while (dbWordRates->next())
// 	{
// 		const auto word = dbWordRates->getString("word");
// 		if (!rates.count(word))
// 			rates[word].push_back(makeGrid<double>());
// 		if (!historicWordRates.count(word))
// 			historicWordRates[word] = makeGrid<double>();
// 		if (!historicDeviations.count(word))
// 			historicDeviations[word] = makeGrid<double>();
// 		for (int i = 0; i < MAP_WIDTH; i++)
// 		{
// 			for (int j = 0; j < MAP_HEIGHT; j++)
// 			{
// 				rates[word].back()[i][j] = stod(dbWordRates->getString(to_string(j*MAP_WIDTH+i)));
// 			}
// 		}
// 	}

// 	profiler.start("getHistoricWordRatesAndDeviation math");
// 	for (int i = 0; i < MAP_WIDTH; i++)
// 	{
// 		for (int j = 0; j < MAP_HEIGHT; j++)
// 		{
// 			for (auto &pair : rates)
// 				for (auto &rate : pair.second)
// 					historicWordRates[pair.first][i][j] += rate[i][j] / PERIODS_IN_HISTORY;

// 			for (auto &pair : rates)
// 				for (auto &rate : pair.second)
// 					historicDeviations[pair.first][i][j] += pow(rate[i][j] - historicWordRates[pair.first][i][j], 2) / PERIODS_IN_HISTORY;

// 			for (auto &pair : rates)
// 				historicDeviations[pair.first][i][j] = pow(historicDeviations[pair.first][i][j], 0.5);
// 		}
// 	}
// 	profiler.stop();

// 	return{ move(historicWordRates), move(historicDeviations) };
// }

// calculate the usage rate of each word at the current time in each cell and the average regional use
void getCurrentLocalAndGlobalRatesForWord(Stats &stats)
{
	for (auto &pair : stats.perWord)
	{
		const auto &localWordCounts = pair.second.currentCounts;
		auto &globalWordRate = pair.second.currentGlobalRate;
		auto &localWordRates = pair.second.currentRates;
		int totalTweets = 0;
		for (int i = 0; i < MAP_WIDTH; i++)
		{
			for (int j = 0; j < MAP_HEIGHT; j++)
			{
				const auto &tweetCount = stats.tweetCounts[i][j];
				if (tweetCount)
				{
					localWordRates[i][j] = (double)localWordCounts[i][j]/tweetCount;
					globalWordRate += localWordCounts[i][j];
					totalTweets += tweetCount;
				}
				else
				{
					localWordRates[i][j] = 0;
				}
			}
		}
		globalWordRate /= totalTweets;
	}
}

void commitStats(const Stats &stats)
{
	string sqlValuesString = "";
	for (const auto &pair : stats.perWord)
	{
		const auto &word = pair.first;
		const auto &statsPerWord = pair.second;

		sqlValuesString += string("(") +
			"FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + "," +
			"'" + word + "',";
		for (int i = 0; i < MAP_WIDTH; i++)
		{
			for (int j = 0; j < MAP_HEIGHT; j++)
			{
				sqlValuesString +=
					to_string(i)                                     + "," +
					to_string(j)                                     + "," +
					to_string(statsPerWord.currentCounts[i][j])      + "," +
					to_string(statsPerWord.currentRates[i][j])       + "," +
					to_string(statsPerWord.historicMeanRates[i][j])  + "," +
					to_string(statsPerWord.historicDeviations[i][j]) + "," +
					"),";
			}
		}
		sqlValuesString.pop_back(); // take the extra comma out
		sqlValuesString += "),";
	}
	sqlValuesString.pop_back();

	connection->createStatement()->execute(
		"INSERT INTO NYC.stat_cache (time,word,x,y,count,rate,historic_mean,historic_deviation) VALUES " + sqlValuesString + " ON DUPLICATE KEY UPDATE time=time;"
		);
}

void detectEvents(const Stats &stats)
{
	mutex listLock;
	queue<string> wordQueue;
	for (const auto &pair : stats.perWord)
	{
		wordQueue.push(pair.first);
	}

	auto detectEventForWord = [&]()
		{
			while (true)
			{
				listLock.lock();
				if (wordQueue.empty())
				{
					listLock.unlock();
					return;
				}
				string word = wordQueue.front();
				wordQueue.pop();
				listLock.unlock();

				const auto &globalWordRate = stats.perWord.at(word).currentGlobalRate;

				double globalDeviation = 0;
				for (int i = 0; i < MAP_WIDTH; i++)
				{
					for (int j = 0; j < MAP_HEIGHT; j++)
					{
						globalDeviation += pow(stats.perWord.at(word).currentRates[i][j] - globalWordRate, 2);
					}
				}
				globalDeviation /= MAP_WIDTH * MAP_HEIGHT;
				globalDeviation = pow(globalDeviation, 0.5);

				// detect events!! and adjust historic rates
				for (int i = 0; i < MAP_WIDTH; i++)
				{
					for (int j = 0; j < MAP_HEIGHT; j++)
					{
						const auto
							&currentLocalWordRate = stats.perWord.at(word).currentRates[i][j],
							&historicWordRate     = stats.perWord.at(word).historicMeanRates[i][j],
							&historicDeviation    = stats.perWord.at(word).historicDeviations[i][j];

						if (
							// checks if a word is a appearing with a greater percentage in one cell than in other cells in the city grid
							(currentLocalWordRate > globalWordRate + SPACIAL_PERCENTAGE_THRESHOLD) &&
							// checks if a word is appearing more frequently in a cell than it has historically in that cell
							(currentLocalWordRate > historicWordRate + TEMPORAL_PERCENTAGE_THRESHOLD) &&
							(currentLocalWordRate > globalWordRate + globalDeviation * SPACIAL_DEVIATIONS_THRESHOLD) &&
							(currentLocalWordRate > historicWordRate + historicDeviation * TEMPORAL_DEVIATIONS_THRESHOLD)
							)
						{
							connection->createStatement()->execute(
								"INSERT INTO NYC.events (time, word, x, y) VALUES (FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + "), '" + word + "'," + to_string(i) + "," + to_string(j) + ");"
								);
							if (VERBOSE_OUTPUT)
							{
								if (!verboseOutputFile.is_open())
									verboseOutputFile.open(verboseOutputFileName, std::ofstream::out | std::ofstream::app);
								verboseOutputFile <<
									word                            + " " +
									to_string(currentLocalWordRate) + " " +
									to_string(globalWordRate)       + " " +
									to_string(historicWordRate)     + " " +
									to_string(globalDeviation)      + " " +
									to_string(historicDeviation)    + "\n";
							}
						}
					}
				}
			}
		};

	vector<thread> threads;
	for (int i = 0; i < THREAD_COUNT; i++)
	{
		threads.emplace_back(detectEventForWord);
	}

	for (int i = 0; i < THREAD_COUNT; i++)
	{
		threads[i].join();
	}
}

unordered_set<string> explode(string const &s)
{
	unordered_set<string> result;
	istringstream iss(s);

	for (string token; getline(iss, token, ' '); )
	{
		transform(token.begin(), token.end(), token.begin(), ::tolower);
		result.insert(token);
	}

	return result;
}

template<typename T> Grid<T> makeGrid()
{
	Grid<T> grid(MAP_WIDTH);
	for (int i = 0; i < MAP_WIDTH; i++)
		grid[i] = vector<T>(MAP_HEIGHT, 0);

	return move(grid);
}

template<typename T> void getArg(T &arg, string section, string option)
{
	static INIReader reader("/srv/etc/config/daemons.ini");
	static double errorValue = -9999;
	arg = (T)reader.GetReal(section, option, errorValue);
	assert(arg != errorValue);
}

// returns pointer to a gaussian blurred 2d array with given dimensions
Grid<double> gaussBlur(const Grid<double> &unblurred_array)
{
	static const double gaussValueMatrix[3] = { 0.22508352, 0.11098164, 0.05472157 }; // mid, perp, diag

	auto& width = MAP_WIDTH;
	auto& height = MAP_HEIGHT;

	// declare a new 2d array to store the blurred values
	auto blurred_array = makeGrid<double>();

	// for each value in the unblurred array, sum the products of that value and each value in the gaussValueMatrix
	for (int j = 0; j < height; j++)
	{
		for (int i = 0; i < width; i++)
		{
			bool left_bound = i == 0, right_bound = i == (width - 1);
			bool top_bound = j == 0, bottom_bound = j == (height - 1);

			// blur the middle
			blurred_array[i][j] += unblurred_array[i][j] * gaussValueMatrix[0];

			if (!left_bound)
			{
				// blur the middle left
				blurred_array[i][j] += unblurred_array[i - 1][j] * gaussValueMatrix[1];

				if (!top_bound)
				{
					//blur the top left
					blurred_array[i][j] += unblurred_array[i - 1][j - 1] * gaussValueMatrix[2];
				}
				if (!bottom_bound)
				{
					// blur the bottom left
					blurred_array[i][j] += unblurred_array[i - 1][j + 1] * gaussValueMatrix[2];
				}
			}

			if (!right_bound)
			{
				// blur the middle right
				blurred_array[i][j] += unblurred_array[i + 1][j] * gaussValueMatrix[1];

				if (!top_bound)
				{
					// blur the top right
					blurred_array[i][j] += unblurred_array[i + 1][j - 1] * gaussValueMatrix[2];
				}
				if (!bottom_bound)
				{
					// blur the bottom right
					blurred_array[i][j] += unblurred_array[i + 1][j + 1] * gaussValueMatrix[2];
				}
			}

			if (!top_bound)
			{
				// blur the top middle
				blurred_array[i][j] += unblurred_array[i][j - 1] * gaussValueMatrix[1];
			}

			if (!bottom_bound)
			{
				// blur the bottom middle
				blurred_array[i][j] += unblurred_array[i][j + 1] * gaussValueMatrix[1];
			}
		}
	}

	return blurred_array;
}
