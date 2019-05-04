#pragma once

#include <chrono>
#include <string>
#include <iostream>
#include <thread>

class TimeKeeper {

	std::chrono::time_point<std::chrono::system_clock, std::chrono::system_clock::duration> programStartTime;
	std::chrono::duration<std::chrono::system_clock::rep, std::chrono::system_clock::period> programDuration;
	std::string title;
	bool running = false;

	void print();

public:
	static int levels;

	TimeKeeper();
	~TimeKeeper();
	void start(std::string);
	void stop();
	double duration();

	void sleep();
};

TimeKeeper::TimeKeeper()
{
	levels++;
}
TimeKeeper::~TimeKeeper()
{
	levels--;
}

void TimeKeeper::start(std::string s) {
	if (running)
	{
		stop();
	}
	running = true;
	title = s;
	programStartTime = std::chrono::system_clock::now();
}

void TimeKeeper::stop() {
	programDuration = std::chrono::system_clock::now() - programStartTime;
	if (running)
	{
		print();
		running = false;
	}
}

double TimeKeeper::duration() {
	return std::chrono::duration_cast<std::chrono::milliseconds>(programDuration).count() / 1000.0;
}


void TimeKeeper::print() {
	std::cout << ">";
	for (int i = 0; i < levels; ++i)
		std::cout << "  ";
	std::cout << title << ": " << std::chrono::duration_cast<std::chrono::milliseconds>(programDuration).count() << std::endl;
}

void TimeKeeper::sleep() {
	std::this_thread::sleep_for(std::chrono::seconds(10000));
}
int TimeKeeper::levels = 0;