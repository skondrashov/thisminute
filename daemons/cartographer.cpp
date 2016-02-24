#include <string>
#include <regex>
#include <fstream>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <cassert>
#include <vector>
#include <iostream>

#include "mysql_connection.h"

#include <cppconn/driver.h>
#include <cppconn/exception.h>
#include <cppconn/resultset.h>
#include <cppconn/statement.h>

#include "INIReader.cpp"

using namespace std;

struct Superevent
{
	int id, start_time, end_time;
	bool* cells;
};

template<typename T> void getArg(T &arg, string section, string option)
{
	static INIReader reader("/srv/etc/config/daemons.ini");
	static double errorValue = -9999;
	arg = (T)reader.GetReal(section, option, errorValue);
	assert(arg != errorValue);
}

int main(int argc, char* argv[])
{
	int LAST_RUN, LOOKBACK_TIME, LOOKAHEAD_TIME;
	double WEST_BOUNDARY, EAST_BOUNDARY, SOUTH_BOUNDARY, NORTH_BOUNDARY, RESOLUTION;

	LAST_RUN = atoi(argv[1]);
	getArg(WEST_BOUNDARY,  "grid",    "west");
	getArg(EAST_BOUNDARY,  "grid",    "east");
	getArg(SOUTH_BOUNDARY, "grid",    "south");
	getArg(NORTH_BOUNDARY, "grid",    "north");
	getArg(RESOLUTION,     "grid",    "cell_size");
	getArg(LOOKBACK_TIME,  "display", "lookback");
	getArg(LOOKAHEAD_TIME, "display", "lookahead");

	const int
		MAP_WIDTH          = static_cast<int>(round(abs((WEST_BOUNDARY  - EAST_BOUNDARY)  / RESOLUTION))),
		MAP_HEIGHT         = static_cast<int>(round(abs((SOUTH_BOUNDARY - NORTH_BOUNDARY) / RESOLUTION)));

	// create a connection
	sql::Connection* connection;
	sql::Driver* driver = get_driver_instance();
	{
		ifstream passwordFile("/srv/etc/auth/daemons/cartographer.pw");
		auto password = static_cast<ostringstream&>(ostringstream{} << passwordFile.rdbuf()).str();
		connection = driver->connect("tcp://127.0.0.1:3306", "cartographer", password);
	}

	while (1) // we will break from within
	{
		string word;
		int eventTime, x, y;
		{
			sql::ResultSet* dbEvent = connection->createStatement()->executeQuery(
					"SELECT *, UNIX_TIMESTAMP(time) AS unix_time FROM NYC.events WHERE mapped = 0 LIMIT 1;"
				);

			if (!(dbEvent->next()))
			{
				break; // https://www.youtube.com/watch?v=4qlCC1GOwFw
			}
			eventTime = stoi(dbEvent->getString("unix_time"));
			word = dbEvent->getString("word");
			x = stoi(dbEvent->getString("x"));
			y = stoi(dbEvent->getString("y"));
			delete dbEvent;
		}

		string query = "SELECT id, word, UNIX_TIMESTAMP(start_time) AS unix_start, UNIX_TIMESTAMP(end_time) AS unix_end, ";

		for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT; i++)
		{
			query += "`" + to_string(i) + "`,";
		}
		query.pop_back(); // take the extra comma out
		query += " FROM NYC.superevents WHERE (";

		// check if event is within superevent location bounds
		bool left_bound = x==0, right_bound  = x==(MAP_WIDTH-1);
		bool top_bound  = y==0, bottom_bound = y==(MAP_HEIGHT-1);

		vector<int> col;

		col.push_back(y*MAP_WIDTH+x);

		if (!left_bound)
		{
			col.push_back(y*MAP_WIDTH+(x-1));

			if (!top_bound)
				col.push_back((y-1)*MAP_WIDTH+(x-1));
			if (!bottom_bound)
				col.push_back((y+1)*MAP_WIDTH+(x-1));
		}

		if (!right_bound)
		{
			col.push_back(y*MAP_WIDTH+(x+1));

			if(!top_bound)
				col.push_back((y-1)*MAP_WIDTH+(x+1));
			if(!bottom_bound)
				col.push_back((y+1)*MAP_WIDTH+(x+1));
		}

		if(!top_bound)
			col.push_back((y-1)*MAP_WIDTH+x);

		if(!bottom_bound)
			col.push_back((y+1)*MAP_WIDTH+x);

		for (unsigned int i = 0; i < col.size(); i++)
		{
			query += "`" + to_string(col[i]) + "`=1";
			if (i != col.size()-1)
			{
				query += " OR ";
			}
		}
		query += ") AND (";
		query += "start_time < FROM_UNIXTIME(" + to_string(eventTime+LOOKAHEAD_TIME) + ") AND end_time >  FROM_UNIXTIME(" + to_string(eventTime-LOOKBACK_TIME) + ")";
		query += ") AND word = '" + word + "';";

		cout << word << " " << y*MAP_WIDTH+x << '\n';

		Superevent superevent;
		superevent.start_time = superevent.end_time = eventTime;
		superevent.cells = new bool[MAP_WIDTH*MAP_HEIGHT]();
		superevent.cells[y*MAP_WIDTH+x] = true;
		{
			sql::ResultSet* dbMatchingSuperevents = connection->createStatement()->executeQuery(
					query
				);
			if (dbMatchingSuperevents->rowsCount() == 1)
			{
				dbMatchingSuperevents->next();
				superevent.start_time = stoi(dbMatchingSuperevents->getString("unix_start"));
				superevent.end_time = stoi(dbMatchingSuperevents->getString("unix_end"));
				superevent.id = stoi(dbMatchingSuperevents->getString("id"));

				if (eventTime < superevent.start_time)
				{
					superevent.start_time = eventTime;
				}
				if (eventTime > superevent.end_time)
				{
					superevent.end_time = eventTime;
				}

				connection->createStatement()->execute(
						"UPDATE NYC.superevents SET start_time=FROM_UNIXTIME(" + to_string(superevent.start_time) + "), " +
						"end_time=FROM_UNIXTIME(" + to_string(superevent.end_time) + "), " +
						"`" + to_string(y*MAP_WIDTH+x) + "`=1 " +
						"WHERE id=" + to_string(superevent.id) + ";"
					);
			}
			else
			{
				// if the event could belong to more than one superevent
				// combine those superevents into one superevent.
				if (dbMatchingSuperevents->rowsCount() > 1)
				{
					Superevent matchedSuperevent;
					matchedSuperevent.cells = new bool[MAP_WIDTH*MAP_HEIGHT]();
					while (dbMatchingSuperevents->next())
					{
						// update the start and end times for the merged superevent
						matchedSuperevent.id = stoi(dbMatchingSuperevents->getString("id"));
						matchedSuperevent.start_time = stoi(dbMatchingSuperevents->getString("unix_start"));
						matchedSuperevent.end_time = stoi(dbMatchingSuperevents->getString("unix_end"));

						if(matchedSuperevent.start_time < superevent.start_time)
							superevent.start_time = matchedSuperevent.start_time;
						if(matchedSuperevent.end_time < superevent.end_time)
							superevent.end_time = matchedSuperevent.end_time;

						// combine all of the cells in the detected superevent into the new merged superevent
						for (int i = 0; i < MAP_WIDTH * MAP_HEIGHT; i++)
						{
							string col = to_string(i);

							// ensures you dont overwrite 1's in the merged superevent with 0's from the current superevent
							if (dbMatchingSuperevents->getString(col) == "1")
								superevent.cells[i] = true;
						}

						// delete the superevent
						string query = "DELETE FROM NYC.superevents WHERE id=" + to_string(matchedSuperevent.id) + ";";
						connection->createStatement()->execute(query);
					}
				}

				string query = "INSERT INTO NYC.superevents (word, start_time, end_time,";
				for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT; i++)
				{
					if (superevent.cells[i] == true)
					{
						query += "`" + to_string(i) + "`,";
					}
				}
				query.pop_back(); // take the extra comma out
				query += ") VALUES ('" + word + "',FROM_UNIXTIME(" + to_string(superevent.start_time) + "),FROM_UNIXTIME(" + to_string(superevent.end_time) + "),";
				for (int i = 0; i < MAP_WIDTH*MAP_HEIGHT; i++)
				{
					if (superevent.cells[i] == true)
					{
						query += "1,";
					}
				}
				query.pop_back(); // take the extra comma out
				query += ");";

				connection->createStatement()->execute(query);
			}

			delete dbMatchingSuperevents;
		}

		connection->createStatement()->execute(
				"UPDATE NYC.events SET mapped=1 WHERE word='" + word + "' AND x=" + to_string(x) + " AND y=" + to_string(y) + " AND time=FROM_UNIXTIME(" + to_string(eventTime) + ");"
			);
	}

	sql::ResultSet* dbSuperevents = connection->createStatement()->executeQuery(
			"SELECT *, UNIX_TIMESTAMP(start_time) AS unix_start, UNIX_TIMESTAMP(end_time) AS unix_end FROM NYC.superevents WHERE end_time > FROM_UNIXTIME(" + to_string(LAST_RUN - LOOKAHEAD_TIME) + ");"
		);

	while (dbSuperevents->next())
	{
		Superevent superevent;
		superevent.start_time = stoi(dbSuperevents->getString("unix_start"));
		superevent.end_time = stoi(dbSuperevents->getString("unix_end"));
		superevent.id = stoi(dbSuperevents->getString("id"));
		int eventLeftBound = 0, eventRightBound = 9, eventBottomBound = 0, eventTopBound = 9;
		string query =
				"INSERT IGNORE INTO NYC.event_tweets SELECT " + to_string(superevent.id) + " AS id, time, lon, lat, exact, user, text FROM NYC.tweets WHERE " +
				"(time BETWEEN FROM_UNIXTIME(" + to_string(superevent.start_time-LOOKBACK_TIME) + ") AND FROM_UNIXTIME(" + to_string(superevent.end_time+LOOKAHEAD_TIME) + ")) " +
				"AND (lon BETWEEN " + to_string(eventLeftBound * RESOLUTION + WEST_BOUNDARY) + " AND " + to_string((eventRightBound+1) * RESOLUTION + WEST_BOUNDARY) + ") " +
				"AND (lat BETWEEN " + to_string(eventBottomBound * RESOLUTION + SOUTH_BOUNDARY) + " AND " + to_string((eventTopBound+1) * RESOLUTION + SOUTH_BOUNDARY) + ") " +
				"AND MATCH(text) AGAINST ('" + dbSuperevents->getString("word") + "' IN BOOLEAN MODE);";
		connection->createStatement()->execute(query);
	}
}
