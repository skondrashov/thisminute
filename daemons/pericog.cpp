#include <string>
#include <regex>
#include <fstream>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <cassert>
#include <cmath>
#include <vector>

#include "mysql_connection.h"

#include <cppconn/driver.h>
#include <cppconn/exception.h>
#include <cppconn/resultset.h>
#include <cppconn/statement.h>

#include "INIReader.h"

#include <array>
#include <vector>
#include <map>
#include <memory>
#include <utility>
#include <thread>
#include <mutex>
#include <queue>

namespace sql {
	class Connection;
	class Driver;
	class ResultSet;
}

using namespace std;

template<class T>
using Grid = vector<vector<T>>;

struct Tweet
{
	Tweet(int x, int y, string text) :
		x(x), y(y), text(text) {}

	int x, y;
	string text;
};

int LOOKBACK_TIME = -1, RECALL_SCOPE, PERIOD, PERIODS_IN_HISTORY;
int MAP_HEIGHT, MAP_WIDTH;
bool HISTORIC_MODE = false, SCAN_EVENTS = false;

double WEST_BOUNDARY, EAST_BOUNDARY, NORTH_BOUNDARY, SOUTH_BOUNDARY, RESOLUTION, SPACIAL_PERCENTAGE_THRESHOLD, TEMPORAL_PERCENTAGE_THRESHOLD, SPACIAL_DEVIATIONS_THRESHOLD, TEMPORAL_DEVIATIONS_THRESHOLD;

const int THREAD_COUNT = 8;

sql::Connection* connection;

unordered_set<string> explode(string const &s);
template<typename T> Grid<T> makeGrid();
template<typename T> void getArg(T &arg, string section, string option);

// write updated historic rates to database
string sqlAppendRates(string word, vector<vector<double>> &wordRates);

void commitRates(string sqlValuesString);

unordered_map<int, Tweet> getUserIdToTweetMap();

// refine each tweet into usable information
Grid<int> refineTweetsAndGetTweetCountPerCell(unordered_map<int, Tweet> &userIdTweetMap);

// load the number of times each word was used in every cell
unordered_map <string, Grid<int>> getCurrentWordCountPerCell(const unordered_map<int, Tweet> &userIdTweetMap);

// load historic word usage rates per cell
pair<unordered_map<string, Grid<double>>, unordered_map<string, Grid<double>>> getHistoricWordRatesAndDeviation();

pair<Grid<double>, double> getCurrentLocalAndGlobalRatesForWord(const Grid<int> &wordCountPerCell, const Grid<int> &tweetCountPerCell);

void detectEvents(
	const unordered_map<string, Grid<int>> &currentWordCountPerCell,
	const unordered_map<string, Grid<double>>    &historicWordRatePerCell,
	const unordered_map<string, Grid<double>>    &historicDeviationByCell,
	const Grid<int>                        &tweetCountPerCell);

Grid<double> gaussBlur(const Grid<double> &unblurred_array);

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
	while ((tmp = getopt(argc, argv, "l:1:2:3:4:Ho")) != -1)
	{
		switch (tmp)
		{
			case 'l':
				LOOKBACK_TIME = stoi(optarg);
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
			case 'H':
				HISTORIC_MODE = true;
				break;
			case 'o':
				SCAN_EVENTS = true;
				break;
		}
	}
	assert(LOOKBACK_TIME != -1);

	MAP_WIDTH = static_cast<int>(round(abs((WEST_BOUNDARY - EAST_BOUNDARY) / RESOLUTION)));
	MAP_HEIGHT = static_cast<int>(round(abs((SOUTH_BOUNDARY - NORTH_BOUNDARY) / RESOLUTION)));
	PERIODS_IN_HISTORY = RECALL_SCOPE / PERIOD;
}

int main(int argc, char* argv[])
{
	Initialize(argc, argv);

	// create a connection
	sql::Driver* driver(get_driver_instance());
	{
		ifstream passwordFile("/srv/etc/auth/daemons/pericog.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		connection = driver->connect("tcp://127.0.0.1:3306", "pericog", password);
	}

	// save all tweets since the specified time to an array
	auto userIdToTweetMap = getUserIdToTweetMap();

	auto tweetCountPerCell = refineTweetsAndGetTweetCountPerCell(userIdToTweetMap);

	auto currentWordCountPerCell = getCurrentWordCountPerCell(userIdToTweetMap);

	string query = "INSERT INTO NYC.words_seen (last_seen,word) VALUES ";
	for (const auto &pair : currentWordCountPerCell)
	{
		query += "(FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + "),'" + pair.first + "'),";
	}
	query.pop_back(); // take the extra comma out

	if (HISTORIC_MODE)
		query += " ON DUPLICATE KEY UPDATE last_seen=@last_seen;";
	else
		query += " ON DUPLICATE KEY UPDATE last_seen=FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ");";

	connection->createStatement()->execute(query);

	unordered_map<string, Grid<double>> historicWordRatePerCell, historicDeviationByCell;
	tie(historicWordRatePerCell, historicDeviationByCell) = getHistoricWordRatesAndDeviation();

	string sqlValuesString = "";
	for (const auto &pair : currentWordCountPerCell)
	{
		const auto& word = pair.first;
		const auto &currentCountByCell = pair.second;

		Grid<double> localWordRateByCell;
		double globalWordRate;

		tie(localWordRateByCell, globalWordRate) = getCurrentLocalAndGlobalRatesForWord(currentCountByCell, tweetCountPerCell);

		if (SCAN_EVENTS)
		{
			detectEvents(currentWordCountPerCell, historicWordRatePerCell, historicDeviationByCell, tweetCountPerCell);
		}

		sqlValuesString += sqlAppendRates(word, localWordRateByCell);
	}
	sqlValuesString.pop_back();
	commitRates(sqlValuesString);
	return 0;
}

// write updated historic rates to database
string sqlAppendRates(string word, Grid<double> &wordRates)
{
	string row = "('" + word + "',FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + "),";
	for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT; i++)
	{
		row += to_string(wordRates[i%MAP_WIDTH][(i-(i%MAP_WIDTH))/MAP_WIDTH]) + ",";
	}
	row.pop_back(); // take the extra comma out
	return row + "),";
}

void commitRates(string sqlValuesString)
{
	string query = "INSERT INTO NYC.rates (word,time,";
	for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT; i++)
	{
		query += "`" + to_string(i) + "`,";
	}
	query.pop_back(); // take the extra comma out
	query += ") VALUES " + sqlValuesString + " ON DUPLICATE KEY UPDATE time=@time;";
	connection->createStatement()->execute(query);
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
		grid[i] = vector<T>(MAP_HEIGHT);

	return grid;
}

template<typename T> void getArg(T &arg, string section, string option)
{
	static INIReader reader("/srv/etc/config/daemons.ini");
	static double errorValue = -9999;
	arg = (T)reader.GetReal(section, option, errorValue);
	assert(arg != errorValue);
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
	unordered_map<string, Grid<int>> wordCountPerCell;
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

	return tweetsPerCell;
}

// refine each tweet into usable information
unordered_map <string, Grid<int>> getCurrentWordCountPerCell(const unordered_map<int, Tweet> &userIdTweetMap)
{
	const int DISCARD_WORDS_WITH_LESS_COUNT = 2; // discard words counted < 2 times
	unordered_map<string, Grid<int>> wordCountPerCell;
	unordered_map<string, int> wordCount;
	

	for (const auto &pair : userIdTweetMap)
	{
		auto tweet = pair.second;

		auto words = explode(tweet.text);
		unsigned int count = 0;
		for (const auto &word : words)
		{
			if (!wordCountPerCell.count(word))
				wordCountPerCell[word] = makeGrid<int>();

			wordCountPerCell[word][tweet.x][tweet.y]++;
			wordCount[word]++;
		}
	}

	// the '&' character is interpreted as the word "amp"... squelch for now
	wordCountPerCell.erase("amp");

	// the word ' ' shows up sometimes... squelch for now
	wordCountPerCell.erase(" ");

	for (const auto& wordCountPair : wordCount)
	{
		if (wordCountPair.second < DISCARD_WORDS_WITH_LESS_COUNT)
			wordCountPerCell.erase(wordCountPair.first);
	}

	return wordCountPerCell;
}

pair<unordered_map<string, Grid<double>>, unordered_map<string, Grid<double>>> getHistoricWordRatesAndDeviation()
{
	unordered_map<string, Grid<double>> historicWordRates, historicDeviations;

	unique_ptr<sql::ResultSet> dbWordRates(connection->createStatement()->executeQuery(
		"SELECT * FROM NYC.rates WHERE time BETWEEN FROM_UNIXTIME(" +
		to_string(LOOKBACK_TIME - RECALL_SCOPE) + ") AND FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ");"
		));

	unordered_map<string, vector<Grid<double>>> rates;

	while (dbWordRates->next())
	{
		const auto word = dbWordRates->getString("word");
		if (!rates.count(word))
			rates[word].push_back(makeGrid<double>());
		if (!historicWordRates.count(word))
			historicWordRates[word] = makeGrid<double>();
		if (!historicDeviations.count(word))
			historicDeviations[word] = makeGrid<double>();
		for (int i = 0; i < MAP_WIDTH; i++)
		{
			for (int j = 0; j < MAP_HEIGHT; j++)
			{
				rates[word].back()[i][j] = stod(dbWordRates->getString(to_string(j*MAP_WIDTH+i)));
			}
		}
	}

	for (int i = 0; i < MAP_WIDTH; i++)
	{
		for (int j = 0; j < MAP_HEIGHT; j++)
		{
			for (auto &pair : rates)
				for (auto &rate : pair.second)
					historicWordRates[pair.first][i][j] += rate[i][j] / PERIODS_IN_HISTORY;

			for (auto &pair : rates)
				for (auto &rate : pair.second)
					historicDeviations[pair.first][i][j] += pow(rate[i][j] - historicWordRates[pair.first][i][j], 2) / PERIODS_IN_HISTORY;

			for (auto &pair : rates)
				historicDeviations[pair.first][i][j] = pow(historicDeviations[pair.first][i][j], 0.5);
		}
	}

	return{ move(historicWordRates), move(historicDeviations) };
}

// calculate the usage rate of each word at the current time in each cell and the average regional use
pair<Grid<double>, double> getCurrentLocalAndGlobalRatesForWord(const Grid<int> &wordCountPerCell, const Grid<int> &tweetCountPerCell)
{
	Grid<double> localWordRates = makeGrid<double>();
	double globalWordRate = 0;
	int totalTweets = 0;
	for (int i = 0; i < MAP_WIDTH; i++)
	{
		for (int j = 0; j < MAP_HEIGHT; j++)
		{
			if (tweetCountPerCell[i][j])
			{
				localWordRates[i][j] = (double)wordCountPerCell[i][j]/tweetCountPerCell[i][j];
				globalWordRate += wordCountPerCell[i][j];
				totalTweets += tweetCountPerCell[i][j];
			}
			else
			{
				localWordRates[i][j] = 0;
			}
		}
	}
	globalWordRate /= totalTweets;

	return{ move(localWordRates), globalWordRate };
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

void detectEvents(
	const unordered_map<string, Grid<int>>    &currentWordCountPerCell,
	const unordered_map<string, Grid<double>> &historicWordRatePerCell,
	const unordered_map<string, Grid<double>> &historicDeviationByCell,
	const Grid<int>                           &tweetCountPerCell
)
{
	mutex listLock;
	queue<string> wordQueue;
	for (const auto &pair : currentWordCountPerCell)
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

				// calculate the usage rate of each word at the current time in each cell and the average regional use
				Grid<double> localWordRateByCell;
				double globalWordRate;
				tie(localWordRateByCell, globalWordRate) = getCurrentLocalAndGlobalRatesForWord(currentWordCountPerCell.at(word), tweetCountPerCell);
				double globalDeviation = 0;
				for (int i = 0; i < MAP_WIDTH; i++)
				{
					for (int j = 0; j < MAP_HEIGHT; j++)
					{
						globalDeviation += pow(localWordRateByCell[i][j] - globalWordRate, 2);
					}
				}
				globalDeviation /= MAP_WIDTH * MAP_HEIGHT;
				globalDeviation = pow(globalDeviation, 0.5);

				// blur the rates over cell borders to reduce noise
				localWordRateByCell = gaussBlur(localWordRateByCell);

				// detect events!! and adjust historic rates
				for (int i = 0; i < MAP_WIDTH; i++)
				{
					for (int j = 0; j < MAP_HEIGHT; j++)
					{
						double historicWordRate = 0, historicDeviation = 0;
						if (historicWordRatePerCell.count(word))
						{
							historicWordRate = historicWordRatePerCell.at(word)[i][j];
							historicDeviation = historicDeviationByCell.at(word)[i][j];
						}

						if (
							// checks if a word is a appearing with a greater percentage in one cell than in other cells in the city grid
							(localWordRateByCell[i][j] > globalWordRate + SPACIAL_PERCENTAGE_THRESHOLD) &&
							// checks if a word is appearing more frequently in a cell than it has historically in that cell
							(localWordRateByCell[i][j] > historicWordRate + TEMPORAL_PERCENTAGE_THRESHOLD) &&
							(localWordRateByCell[i][j] > globalWordRate + globalDeviation * SPACIAL_DEVIATIONS_THRESHOLD) &&
							(localWordRateByCell[i][j] > historicWordRate + historicDeviation * TEMPORAL_DEVIATIONS_THRESHOLD)
							)
						{
							if (!HISTORIC_MODE)
							{
								connection->createStatement()->execute(
									"INSERT INTO NYC.events (time, word, x, y) VALUES (FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + "), '" + word + "'," + to_string(i) + "," + to_string(j) + ");"
									);
							}
							{
								ofstream resultFile;
								resultFile.open ("/root/test/" +
									to_string(SPACIAL_PERCENTAGE_THRESHOLD) + "_" +
									to_string(TEMPORAL_PERCENTAGE_THRESHOLD) + "_" +
									to_string(SPACIAL_DEVIATIONS_THRESHOLD) + "_" +
									to_string(TEMPORAL_DEVIATIONS_THRESHOLD) +
									".txt", std::ofstream::out | std::ofstream::app);
								resultFile << "word: " << word << "\n";
								resultFile.close();
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