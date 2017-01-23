#include <string>

using namespace std;

struct Tweet
{
	static Tweet* delimiter;

	bool important = false;

	bool require_update = true;
	double core_distance, smallest_reachability_distance;

	unsigned int time;
	double lat, lon;
	string text, user;
	bool exact;
	vector<double> feature_vector;

	unsigned int x, y;
	string clean_text;
	unordered_set<string> words;
	multimap<double, Tweet*> optics_neighbors;
	unordered_map<Tweet*, double> optics_distances;
	unordered_map<string, double> regional_word_rates;

	Tweet(int _time, double _lat, double _lon, string _text, string _user, bool _exact, vector<double> _feature_vector)
		: time(_time), lat(_lat), lon(_lon), text(_text), user(_user), exact(_exact), feature_vector(_feature_vector)
	{}
	void clean();
	~Tweet();

private:
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
};
