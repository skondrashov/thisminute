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

#include "INIReader.cpp"

#include <array>
#include <vector>
#include <map>
#include <memory>

namespace sql {
	class Connection;
	class Driver;
}

using namespace std;

int LOOKBACK_TIME, RECALL_SCOPE, PERIOD, PERIODS_IN_HISTORY;
int MAP_HEIGHT, MAP_WIDTH;

double WEST_BOUNDARY, EAST_BOUNDARY, NORTH_BOUNDARY, SOUTH_BOUNDARY, RESOLUTION, SPACIAL_DEVIATION_THRESHOLD, TEMPORAL_DEVIATION_THRESHOLD;

unique_ptr<sql::Connection> connection;

struct Tweet
{
	Tweet(int x, int y, string text) :
		x(x), y(y), text(text){}

	int x, y;
	string text;
};

unordered_set<string> explode(string const &s);
template<typename T> vector<vector<T>> makeGrid(int width, int height);

template<typename T> void getArg(T &arg, string section, string option);

map<int, Tweet> getUserIdToTweetMap(sql::Connection connection);

// refine each tweet into usable information
vector<vector<int>> refineTweetsAndGetTweetCountPerCell(unordered_map<int, Tweet> userIdTweetMap);

// load the number of times each word was used in every cell
unordered_map <string, vector<vector<int>>> getWordCountPerCell(unordered_map<int, Tweet> userIdTweetMap);

// load historic word usage rates per cell
unordered_map<string, vector<vector<double>>> getHistoricWordRates();

void detectEvents(
	unordered_map<string, int**>      currentWordRates,
	unordered_map<string, double**>   historicWordRates,
	double**                          localWordRates,
	double                            globalWordRate,
	int                               MAP_WIDTH,
	int                               MAP_HEIGHT,
	double                            SPACIAL_DEVIATION_THRESHOLD,
	double                            TEMPORAL_DEVIATION_THRESHOLD)

double** gaussBlur(double** unblurred_array, int width, int height);

void Initialize()
{
	getArg(RECALL_SCOPE,                 "timing",    "history");
	getArg(PERIOD,                       "timing",    "period");
	getArg(WEST_BOUNDARY,                "grid",      "west");
	getArg(EAST_BOUNDARY,                "grid",      "east");
	getArg(SOUTH_BOUNDARY,               "grid",      "south");
	getArg(NORTH_BOUNDARY,               "grid",      "north");
	getArg(RESOLUTION,                   "grid",      "cell_size");
	getArg(SPACIAL_DEVIATION_THRESHOLD,  "threshold", "spacial");
	getArg(TEMPORAL_DEVIATION_THRESHOLD, "threshold", "temporal");

	MAP_WIDTH  = static_cast<int>(round(abs((WEST_BOUNDARY -  EAST_BOUNDARY)  / RESOLUTION)));
	MAP_HEIGHT = static_cast<int>(round(abs((SOUTH_BOUNDARY - NORTH_BOUNDARY) / RESOLUTION)));
	PERIODS_IN_HISTORY = RECALL_SCOPE / PERIOD;
}

int main(int argc, char* argv[])
{
	LOOKBACK_TIME = atoi(argv[1]);

	Initialize();

	// create a connection
	unique_ptr<sql::Driver> driver(get_driver_instance());
	{
		ifstream passwordFile("/srv/etc/auth/daemons/pericog.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		connection = driver->connect("tcp://127.0.0.1:3306", "pericog", password);
	}

	// save all tweets since the specified time to an array
	auto userIdToTweetMap = getUserIdToTweetMap(connection.get());

	auto tweetCountPerCell = refineTweetsAndGetTweetCountPerCell(userIdToTweetMap);

	auto wordCountPerCell = getWordCountPerCell(userIdToTweetMap);

	string query = "INSERT INTO NYC.words_seen (time,word) VALUES ";
	for (const auto &pair : wordCountPerCell)
	{
		query += "(FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + "),'" + pair.first + "'),";
	}
	query.pop_back(); // take the extra comma out
	query += " ON DUPLICATE KEY UPDATE last_seen=FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ");"
	connection->createStatement()->execute(query);

	auto historicWordRates = getHistoricWordRates();

	// consider historic rates that are no longer in use as being currently in use at a rate of 0
	for (const auto &pair : historicWordRates)
	{
		const auto& word = pair.first;
		if (!wordCountPerCell.count(word))
			wordCountPerCell[word] = makeGrid<int>(MAP_WIDTH, MAP_HEIGHT);
	}

	for (const auto &pair : wordCountPerCell)
	{
		const auto& word = pair.first;
		auto &grid = pair.second;

		// calculate the usage rate of each word at the current time in each cell and the average regional use
		vector<vector<double>> localWordRates = makeGrid<double>(MAP_WIDTH, MAP_HEIGHT);
		// calculate the usage rate of each word at the current time in each cell and the average regional use
		double** localWordRates = makeGrid<double>(MAP_WIDTH, MAP_HEIGHT);
		double globalWordRate = 0, globalDeviation = 0;
		{
			int totalTweets = 0;
			for (int i = 0; i < MAP_WIDTH; i++)
			{
				for (int j = 0; j < MAP_HEIGHT; j++)
				{
					if (tweetsPerCell[i][j])
					{
						localWordRates[i][j] = (double)grid[i][j]/tweetsPerCell[i][j];
						globalWordRate += grid[i][j];
						totalTweets += tweetsPerCell[i][j];
					}
					else
					{
						localWordRates[i][j] = 0;
					}
				}
			}
			globalWordRate /= totalTweets;

			for (int i = 0; i < MAP_WIDTH; i++)
			{
				for (int j = 0; j < MAP_HEIGHT; j++)
				{
					globalDeviation += pow(localWordRates[i][j] - globalWordRate, 2) / (MAP_WIDTH * MAP_HEIGHT);
				}
			}
			globalDeviation = pow(globalDeviation, 0.5);
		}

		// blur the rates over cell borders to reduce noise
		localWordRates = gaussBlur(localWordRates, MAP_WIDTH, MAP_HEIGHT);

		// detect events!! and adjust historic rates
		for (int i = 0; i < MAP_WIDTH; i++)
		{
			for (int j = 0; j < MAP_HEIGHT; j++)
			{
				if (
					// checks if a word is a appearing with a greater percentage in one cell than in other cells in the city grid
					(localWordRates[i][j] > globalWordRate + SPACIAL_PERCENTAGE_THRESHOLD) &&
					// checks if a word is appearing more frequently in a cell than it has historically in that cell
					(localWordRates[i][j] > historicWordRates[word][i][j] + TEMPORAL_PERCENTAGE_THRESHOLD) &&
					(localWordRates[i][j] > historicWordRates[word][i][j] + globalDeviation * SPACIAL_DEVIATION_THRESHOLD) &&
					(localWordRates[i][j] > historicWordRates[word][i][j] + historicDeviations[word][i][j] * TEMPORAL_DEVIATION_THRESHOLD)
				)
				{
					connection->createStatement()->execute(
						"INSERT INTO NYC.events (word, x, y) VALUES ('" + word + "'," + to_string(i) + "," + to_string(j) + ");"
						);
				}
			}
		}

		// write updated historic rates to database
		string* values  = new string[MAP_WIDTH*MAP_HEIGHT];
		for (int j = 0; j < MAP_HEIGHT; j++)
		{
			for (int i = 0; i < MAP_WIDTH; i++)
			{
				values[j*MAP_WIDTH+i+1]  = to_string(localWordRates[i][j]);
			}
		}

		"('" + word + "',FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + "),";
		for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT; i++)
		{
			sqlValuesString += values[i] + ",";
		}
	}
	sqlValuesString.pop_back(); // take the extra comma out

	string query = "INSERT INTO NYC.rates (word,time,";
	string* columns = new string[MAP_WIDTH*MAP_HEIGHT];
	for (int j = 0; j < MAP_HEIGHT; j++)
	{
		for (int i = 0; i < MAP_WIDTH; i++)
		{
			columns[j*MAP_WIDTH+i+1] = to_string(j*MAP_WIDTH+i);
		}
	}
	for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT; i++)
	{
		query += "`" + columns[i] + "`,";
	}
	query.pop_back(); // take the extra comma out
	query += ") VALUES ";

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

template<typename T> vector<vector<T>> makeGrid(int width, int height)
{
	vector<vector<T>> grid(MAP_WIDTH);
	for (int i = 0; i < width; i++)
	{
		grid[i] = vector<T>(MAP_HEIGHT);
	}

	return grid;
}

// returns pointer to a gaussian blurred 2d array with given dimensions
double** gaussBlur(double** unblurred_array, int width, int height)
{
	static const double gaussValueMatrix[3] = {0.22508352, 0.11098164, 0.05472157}; // mid, perp, diag

	// declare a new 2d array to store the blurred values
	double** blurred_array = new double*[width];
	for(int i = 0; i < width; ++i)
		blurred_array[i] = new double[height]();

	// for each value in the unblurred array, sum the products of that value and each value in the gaussValueMatrix

	for(int j = 0; j < height; j++)
	{
		for(int i = 0; i < width; i++)
		{
			bool left_bound = i==0, right_bound = i==(width-1);
			bool top_bound = j==0, bottom_bound = j==(height-1);

			// blur the middle
			blurred_array[i][j] += unblurred_array[i][j] * gaussValueMatrix[0];

			if (!left_bound)
			{
				// blur the middle left
				blurred_array[i][j] += unblurred_array[i-1][j] * gaussValueMatrix[1];

				if (!top_bound)
				{
					//blur the top left
					blurred_array[i][j] += unblurred_array[i-1][j-1] * gaussValueMatrix[2];
				}
				if (!bottom_bound)
				{
					// blur the bottom left
					blurred_array[i][j] += unblurred_array[i-1][j+1] * gaussValueMatrix[2];
				}
			}

			if (!right_bound)
			{
				// blur the middle right
				blurred_array[i][j] += unblurred_array[i+1][j] * gaussValueMatrix[1];

				if(!top_bound)
				{
				// blur the top right
				blurred_array[i][j] += unblurred_array[i+1][j-1] * gaussValueMatrix[2];
				}
				if(!bottom_bound)
				{
				// blur the bottom right
				blurred_array[i][j] += unblurred_array[i+1][j+1] * gaussValueMatrix[2];
				}
			}

			if(!top_bound)
			{
				// blur the top middle
				blurred_array[i][j] += unblurred_array[i][j-1] * gaussValueMatrix[1];
			}

			if(!bottom_bound)
			{
				// blur the bottom middle
				blurred_array[i][j] += unblurred_array[i][j+1] * gaussValueMatrix[1];
			}
		}
	}

	return blurred_array;
}

template<typename T> void getArg(T &arg, string section, string option)
{
	static INIReader reader("/srv/etc/config/daemons.ini");
	static double errorValue = -9999;
	arg = (T)reader.GetReal(section, option, errorValue);
	assert(arg != errorValue);
}

unordered_map<int, Tweet> getUserIdToTweetMap(sql::Connection connection)
{
	unordered_map<int, Tweet> tweets;
	unique_ptr<sql::ResultSet> dbTweets(connection.createStatement()->executeQuery(
		"SELECT * FROM NYC.tweets WHERE time > FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ");")
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
vector<vector<int>> refineTweetsAndGetTweetCountPerCell(unordered_map<int, Tweet> userIdTweetMap)
{
	unordered_map<string, vector<vector<int>>> wordCountPerCell;
	auto tweetsPerCell = makeGrid<int>(MAP_WIDTH, MAP_HEIGHT);

	for (auto &pair : userIdTweetMap)
	{
		auto &tweet = pair.second;

		// remove mentions and URLs
		regex mentionsAndUrls("((\\B@)|(\\bhttps?:\\/\\/))[^\\s]+");
		tweet.text = regex_replace(tweet.text, mentionsAndUrls, string(" "));

		// remove all non-word characters
		regex nonWord("[^\\w]+");
		tweet.text = regex_replace(tweet.text, nonWord, string(" "));

		tweetsPerCell[tweet.x][tweet.y]++;
	}

	return tweetsPerCell;
}

// refine each tweet into usable information
unordered_map <string, vector<vector<int>>> getWordCountPerCell(unordered_map<int, Tweet> userIdTweetMap)
{
	unordered_map<string, vector<vector<int>>> wordCountPerCell;

	for (const auto &pair : userIdTweetMap)
	{
		auto tweet = pair.second;

		auto words = explode(tweet.text);
		for (const auto &word : words)
		{
			if (!wordCountPerCell.count(word))
				wordCountPerCell[word] = makeGrid<int>(MAP_WIDTH, MAP_HEIGHT);

			wordCountPerCell[word][tweet.x][tweet.y]++;
		}
	}

	// the '&' character is interpreted as the word "amp"... squelch for now
	wordCountPerCell.erase("amp");

	// the word ' ' shows up sometimes... squelch for now
	wordCountPerCell.erase(" ");

	return wordCountPerCell;
}

unordered_map<string, vector<vector<double>>> getHistoricWordRates()
{
	unordered_map<string, vector<vector<double>>> historicWordRates, historicDeviations;

	unique_ptr<sql::ResultSet> dbWordsSeen(connection->createStatement()->executeQuery(
		"SELECT * FROM NYC.words_seen;"
		));

	while (dbWordsSeen->next())
	{
		const auto word = dbWordsSeen->getString("word");
		unique_ptr<sql::ResultSet> wordRates(connection->createStatement()->executeQuery(
			"SELECT * FROM NYC.rates WHERE word ='" + word + "' AND time BETWEEN FROM_UNIXTIME(" +
			to_string(LOOKBACK_TIME) + ") AND FROM_UNIXTIME(" + to_string(LOOKBACK_TIME - RECALL_SCOPE) + ") ORDER BY time DESC;"
			));

		historicWordRates[word]  = makeGrid<double>(MAP_WIDTH, MAP_HEIGHT, true);
		historicDeviations[word] = makeGrid<double>(MAP_WIDTH, MAP_HEIGHT, true);
		vector<vector<vector<double>>> rates;

		while (wordRates->next())
		{
			rates.push_back(makeGrid<double>(MAP_WIDTH, MAP_HEIGHT));
			for (int i = 0; i < MAP_WIDTH; i++)
			{
				for (int j = 0; j < MAP_HEIGHT; j++)
				{
					rates.back()[i][j] = stod(wordRates->getString('`' + to_string(j*MAP_WIDTH+i) + '`'));
				}
			}
		}

		for (int i = 0; i < MAP_WIDTH; i++)
		{
			for (int j = 0; j < MAP_HEIGHT; j++)
			{
				for (const auto &rate : rates)
				{
					historicWordRates[word][i][j] += rate[i][j] / PERIODS_IN_HISTORY;
				}
				for (const auto &rate : rates)
				{
					historicDeviations[word][i][j] += pow(rate[i][j] - historicWordRates[word][i][j], 2) / PERIODS_IN_HISTORY;
				}
				historicDeviations[word][i][j] = pow(historicDeviations[word][i][j], 0.5);
			}
		}
	}

	return historicWordRates;
}

void detectEvents(
	unordered_map<string, int**>      currentWordRates,
	unordered_map<string, double**>   historicWordRates,
	double**                          localWordRates,
	double                            globalWordRate,
	int                               MAP_WIDTH,
	int                               MAP_HEIGHT,
	double                            SPACIAL_DEVIATION_THRESHOLD,
	double                            TEMPORAL_DEVIATION_THRESHOLD)
{
	for (const auto &pair : currentWordRates)
		{
		// detect events!! and adjust historic rates
		for (int i = 0; i < MAP_WIDTH; i++)
		{
			for (int j = 0; j < MAP_HEIGHT; j++)
			{
				if (
					// checks if a word is a appearing with a greater percentage in one cell than in other cells in the city grid
					(localWordRates[i][j] > globalWordRate + SPACIAL_DEVIATION_THRESHOLD) &&
					// checks if a word is appearing more frequently in a cell than it has historically in that cell
					(localWordRates[i][j] > historicWordRates[word][i][j] + TEMPORAL_DEVIATION_THRESHOLD))
					{
					connection->createStatement()->execute(
						"INSERT INTO NYC.events (word, x, y) VALUES ('" + word + "'," + to_string(i) + "," + to_string(j) + ");"
					);
					}
				}
			}
		}
}