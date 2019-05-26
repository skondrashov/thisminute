extern crate twitter_stream;
extern crate ini;

use twitter_stream::{Token, TwitterStreamBuilder};
use twitter_stream::rt::{self, Future, Stream};
use ini::Ini;

fn read_section<'a>(config: &'a Ini, section: &str, values: &[&str]) -> Vec<&'a str> {
	let section = config.section(Some(section))
		.expect(&format!("No '{}' section found in config", section));
	let mut results = vec![];
	for &value in values {
		results.push(
			&section.get(value)
				.expect(&format!("Unable to find value for '{}' in config", value))[..]
		);
	}
	results
}

fn main() {
	let config = Ini::load_from_file("config.ini")
		.expect("Unable to read config.ini");

	let bounds = read_section(
		&config,
		"geo_bounding",
		&["west", "south", "east", "north"],
	);
	let bounds = {
		let mut results = vec![];
		for bound in bounds {
			results.push(
				bound
					.parse::<f64>()
					.expect(&format!("Unable to parse bound in config"))
			);
		}
		&[((results[0], results[1]), (results[2], results[3]))][..]
	};

	let twitter_auth = read_section(
		&config,
		"twitter_auth",
		&["consumer_key", "consumer_secret", "access_token", "access_secret"],
	);

	let future = TwitterStreamBuilder::filter(
		Token::new(twitter_auth[0], twitter_auth[1], twitter_auth[2], twitter_auth[3])
	)
		.locations(bounds)
		.listen()
		.unwrap()
		.flatten_stream()
		.for_each(|json| {
			println!("{}", json);
			Ok(())
		})
		.map_err(|e| println!("error: {}", e));

	rt::run(future);
}
