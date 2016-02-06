#include <string>
#include <regex>
#include <fstream>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <cassert>

#include "mysql_connection.h"

#include <cppconn/driver.h>
#include <cppconn/exception.h>
#include <cppconn/resultset.h>
#include <cppconn/statement.h>

#include "INIReader.cpp"

using namespace std;

struct Tweet
{
	double lon, lat;
	string text;
};

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

template<typename T> T** makeGrid(int width, int height, bool init = false)
{
	T** grid = new T*[width];
	for (int i = 0; i < width; i++)
	{
		if (init)
		{
			grid[i] = new T[height]();
		}
		else
		{
			grid[i] = new T[height];
		}
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
	static INIReader reader("/srv/config/daemons.ini");
	static double errorValue = -9999;
	arg = (T)reader.GetReal(section, option, errorValue);
	assert(arg != errorValue);
}

int main(int argc, char* argv[])
{
	int LOOKBACK_TIME, RECALL_SCOPE, PERIOD;
	double WEST_BOUNDARY, EAST_BOUNDARY, SOUTH_BOUNDARY, NORTH_BOUNDARY, RESOLUTION, SPACIAL_DEVIATION_THRESHOLD, TEMPORAL_DEVIATION_THRESHOLD;

	LOOKBACK_TIME = atoi(argv[1]);
	getArg(RECALL_SCOPE,                 "timing",    "history");
	getArg(PERIOD,                       "timing",    "period");
	getArg(WEST_BOUNDARY,                "grid",      "west");
	getArg(EAST_BOUNDARY,                "grid",      "east");
	getArg(SOUTH_BOUNDARY,               "grid",      "south");
	getArg(NORTH_BOUNDARY,               "grid",      "north");
	getArg(RESOLUTION,                   "grid",      "cell_size");
	getArg(SPACIAL_DEVIATION_THRESHOLD,  "threshold", "spacial");
	getArg(TEMPORAL_DEVIATION_THRESHOLD, "threshold", "temporal");

	const int
		MAP_WIDTH          = static_cast<int>(round(abs((WEST_BOUNDARY  - EAST_BOUNDARY)  / RESOLUTION))),
		MAP_HEIGHT         = static_cast<int>(round(abs((SOUTH_BOUNDARY - NORTH_BOUNDARY) / RESOLUTION))),
		PERIODS_IN_HISTORY = RECALL_SCOPE/PERIOD;

	// create a connection
	sql::Connection* connection;
	sql::Driver* driver = get_driver_instance();
	{
		ifstream passwordFile("/srv/auth/daemons/pericog.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		connection = driver->connect("tcp://127.0.0.1:3306", "pericog", password);
	}

	// save all tweets since the specified time to an array
	unordered_map<int, Tweet> tweets;
	{
		sql::ResultSet* dbTweets = connection->createStatement()->executeQuery(
				"SELECT * FROM NYC.tweets WHERE time > FROM_UNIXTIME(" + to_string(LOOKBACK_TIME) + ") limit 1000;"
			);
		while (dbTweets->next())
		{
			int userId = stoi(dbTweets->getString("user"));
			if (tweets.count(userId))
			{
				// combine all tweets from a single user for the purposes of word counting
				// location will be inaccurate for some words, but not often enough to matter (hopefully)
				tweets[userId].text += " " + dbTweets->getString("text");
			}
			else
			{
				tweets[userId].lon  = stod(dbTweets->getString("lon"));
				tweets[userId].lat  = stod(dbTweets->getString("lat"));
				tweets[userId].text = dbTweets->getString("text");
			}
		}
		delete dbTweets;
	}

	// refine each tweet into usable information
	unordered_map<string, int**> currentWordRates;
	auto tweetsPerCell = makeGrid<int>(MAP_WIDTH, MAP_HEIGHT, true);
	{
		for (const auto &pair : tweets)
		{
			auto tweet = pair.second;

			// if a tweet is located outside of the grid, ignore it and go to the next tweet
			if (tweet.lon < WEST_BOUNDARY || tweet.lon > EAST_BOUNDARY
				|| tweet.lat < SOUTH_BOUNDARY || tweet.lat > NORTH_BOUNDARY)
			{
				continue;
			}

			const int
				x = floor((tweet.lon - WEST_BOUNDARY)  / RESOLUTION),
				y = floor((tweet.lat - SOUTH_BOUNDARY) / RESOLUTION);

			// remove mentions and URLs
			regex mentionsAndUrls ("((\\B@)|(\\bhttps?:\\/\\/))[^\\s]+");
			tweet.text = regex_replace(tweet.text, mentionsAndUrls, string(" "));

			// remove all non-word characters
			regex nonWord ("[^\\w]+");
			tweet.text = regex_replace(tweet.text, nonWord, string(" "));

			auto words = explode(tweet.text);
			for (const auto &word : words)
			{
				if (!currentWordRates.count(word))
				{
					currentWordRates[word] = makeGrid<int>(MAP_WIDTH, MAP_HEIGHT, true);
				}
				currentWordRates[word][x][y]++;
			}
			tweetsPerCell[x][y]++;
		}

		// the '&' character is interpreted as the word "amp"... squelch for now
		currentWordRates.erase("amp");

		// the word ' ' shows up sometimes... squelch for now
		currentWordRates.erase(" ");
	}

	// load historic word usage rates per cell
	unordered_map<string, double**> historicWordRates;
	{
		sql::ResultSet* dbHistoricWordRates = connection->createStatement()->executeQuery(
				"SELECT * FROM NYC.rates;"
			);
		while (dbHistoricWordRates->next())
		{
			const auto word = dbHistoricWordRates->getString("word");
			historicWordRates[word] = makeGrid<double>(MAP_WIDTH, MAP_HEIGHT);
			for (int i = 0; i < MAP_WIDTH; i++)
			{
				for (int j = 0; j < MAP_HEIGHT; j++)
				{
					historicWordRates[word][i][j] = stod(dbHistoricWordRates->getString(to_string(j*MAP_WIDTH+i)));
				}
			}
		}
		delete dbHistoricWordRates;
	}

	// consider historic rates that are no longer in use as being currently in use at a rate of 0
	for (const auto &pair : historicWordRates)
	{
		const auto word = pair.first;
		if (!currentWordRates.count(word))
		{
			currentWordRates[word] = makeGrid<int>(MAP_WIDTH, MAP_HEIGHT, true);
		}
	}

	for (const auto &pair : currentWordRates)
	{
		const auto word = pair.first;
		auto grid = pair.second;

		// consider new uses of a word as being historically used at a rate of 0
		if (!historicWordRates.count(word))
		{
			historicWordRates[word] = makeGrid<double>(MAP_WIDTH, MAP_HEIGHT, true);
		}

		// calculate the usage rate of each word at the current time in each cell and the average regional use
		double** localWordRates = makeGrid<double>(MAP_WIDTH, MAP_HEIGHT);
		double globalWordRate = 0;
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
		}

		// blur the rates over cell borders to reduce noise
		localWordRates = gaussBlur(localWordRates, MAP_WIDTH, MAP_HEIGHT);

		// detect events!! and adjust historic rates
		for (int i = 0; i < MAP_WIDTH; i++)
		{
			for (int j = 0; j < MAP_HEIGHT; j++)
			{
				if (
					(localWordRates[i][j] > globalWordRate + SPACIAL_DEVIATION_THRESHOLD) &&
					(localWordRates[i][j] > historicWordRates[word][i][j] + TEMPORAL_DEVIATION_THRESHOLD)
				)
				{
					connection->createStatement()->execute(
							"INSERT INTO NYC.events (word, x, y) VALUES ('" + word + "'," + to_string(i) + "," + to_string(j) + ");"
						);
				}
				historicWordRates[word][i][j] *= ((double)PERIODS_IN_HISTORY - 1) / PERIODS_IN_HISTORY;
				historicWordRates[word][i][j] += localWordRates[i][j] / PERIODS_IN_HISTORY;
			}
		}

		// write updated historic rates to database
		string* columns = new string[MAP_WIDTH*MAP_HEIGHT+1];
		string* values  = new string[MAP_WIDTH*MAP_HEIGHT+1];
		columns[0] = "word";
		values[0]  = "'" + word + "'";
		for (int j = 0; j < MAP_HEIGHT; j++)
		{
			for (int i = 0; i < MAP_WIDTH; i++)
			{
				columns[j*MAP_WIDTH+i+1] = to_string(j*MAP_WIDTH+i);
				values[j*MAP_WIDTH+i+1]  = to_string(historicWordRates[word][i][j]);
			}
		}
		string query = "INSERT INTO NYC.rates (";
		for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT+1; i++)
		{
			query += "`" + columns[i] + "`,";
		}
		query.pop_back(); // take the extra comma out
		query += ") VALUES (";
		for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT+1; i++)
		{
			query += values[i] + ",";
		}
		query.pop_back(); // take the extra comma out
		query += ") ON DUPLICATE KEY UPDATE ";
		for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT+1; i++)
		{
			query += "`" + columns[i] + "`=" + values[i] + ",";
		}
		query.pop_back(); // take the extra comma out
		query += ";";

		connection->createStatement()->execute(query);
	}
}
