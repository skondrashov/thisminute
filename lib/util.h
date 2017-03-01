#pragma once

#include <string>
#include <unordered_set>
#include <vector>

namespace TMUtil
{
	std::unordered_set<string> explode(std::string const &s)
	{
		std::istringstream iss(s);
		std::unordered_set<std::string> result;
		for (std::string token; std::getline(iss, token, ' '); )
		{
			if (token == "" || token == " ")
				cout << "we might still need this\n";
			result.insert(token);
		}

		return result;
	}

	std::vector<double> parseJSONVector(const std::string &s, const int size)
	{
		std::istringstream iss(s.substr(1, s.size()-2));
		std::vector<double> result;
		result.reserve(size);
		for (std::string token; std::getline(iss, token, ','); )
		{
			result.push_back(stod(token));
		}

		return result;
	}
}