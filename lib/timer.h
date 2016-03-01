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

	void start(std::string);
	void stop();
	double duration();

	void sleep();
};

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
	std::cout << std::endl << title << ": " << std::chrono::duration_cast<std::chrono::milliseconds>(programDuration).count() << std::endl;
}

void TimeKeeper::sleep() {
	std::this_thread::sleep_for(std::chrono::seconds(10000));
}