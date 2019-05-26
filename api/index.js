const
	fs = require('fs'),
	ini = require('ini'),
	config = ini.parse(fs.readFileSync('./config.ini', 'utf-8'));

const
	express = require('express'),
	bodyParser = require('body-parser'),
	cors = require('cors'),
	app = express();
app.use(cors());
app.use(bodyParser.json());

const
	{ Pool } = require('pg'),
	pgClient = new Pool({
		user: config.db_auth.username,
		host: config.connections[config.connections.active],
		database: 'thisminute',
		password: config.db_auth.password,
	});
pgClient.on('error', () => console.log('Lost PG connection'));

// // Redis Client Setup
// const redis = require('redis');
// const redisClient = redis.createClient({
//   host: keys.redisHost,
//   port: keys.redisPort,
//   retry_strategy: () => 1000
// });
// const redisPublisher = redisClient.duplicate();

// $texts = [];
// foreach (pg_fetch_all($result) as $row) {
// 	$texts []= $row['text'];
// }

// if (!empty($_GET['format'])) {
// 	echo implode("<br>", $texts);
// } else {
// 	echo json_encode($texts);
// }

app.get('/tweets/:limit/:format', async (req, res) => {
	const
		limit = Math.max(Math.min(100, parseInt(req.params.limit)), 1) || 1,
		format = req.params.format || false,
		values = await pgClient.query(`
			SELECT text FROM tweets ORDER BY id DESC LIMIT $1
		`, [limit]);

	res.send(values.rows);
});

app.get('/markers', async (req, res) => {
	const events = await pgClient.query(`
			SELECT * FROM events
		`);
	let count = await pgClient.query(`
			SELECT
				0 AS count
			FROM tweets
			LIMIT 1
		`);

	switch (config.display.source) {
		case 'crowdflower':
			tweets = await pgClient.query(`
					SELECT
						*,
						ST_X(geo::geometry) AS lon,
						ST_Y(geo::geometry) AS lat
					FROM tweets
					WHERE id IN (
						SELECT tv.tweet_id
						FROM tweet_votes tv
						LEFT JOIN tweet_votes tv2 ON
							tv2.tweet_id = tv.tweet_id AND
							tv2.user_ip = $1
						WHERE
							tv.user_ip = '1.1.1.1' AND (
								tv2.submit IS NULL OR
								tv2.submit = FALSE
							)
					)
					ORDER BY id DESC
					LIMIT 20
				`, [
					req.headers['x-forwarded-for'],
				]);
			count = await pgClient.query(`
					SELECT COUNT(*) AS count
					FROM tweet_votes tv
					LEFT JOIN tweet_votes tv2 ON
						tv2.tweet_id = tv.tweet_id AND
						tv2.user_ip = $1
					WHERE
						tv.user_ip = '1.1.1.1' AND (
							tv2.submit IS NULL OR
							tv2.submit = FALSE
						)
				`, [
					req.headers['x-forwarded-for'],
				]);
			break;
		case 'all':
			tweets = await pgClient.query(`
					SELECT
						*,
						ST_X(geo::geometry) AS lon,
						ST_Y(geo::geometry) AS lat
					FROM tweets
					ORDER BY id DESC
					LIMIT 50
				`);
			break;
		case 'breaking':
			tweets = await pgClient.query(`
					SELECT
						*,
						ST_X(geo::geometry) AS lon,
						ST_Y(geo::geometry) AS lat
					FROM tweets
					JOIN tweet_votes ON
						id=tweet_id
					WHERE
						user_ip = '0.0.0.0' AND
						disaster = TRUE
					ORDER BY id DESC
					LIMIT 20
				`);
			break;
	}

	res.send({
		events: events.rows || [],
		tweets: tweets.rows || [],
		count: count.rows[0].count,
	});
});

app.post('/vote', async (req, res) => {
	let data = req.body;
	data.tweet_id = data.id;
	data.user_ip = req.headers['x-forwarded-for'];

	if (!(
		data.tweet_id &&
		[
			'172.18.0.1',
			'76.206.40.123',
			'24.128.191.208',
			'104.191.244.200',
			'68.32.143.90',
		].includes(data.user_ip)
	))
	{
		res.send('invalid request');
		return;
	}

	let
		columns = [],
		values = [],
		updates = [],
		params = [],
		i = 1;

	[
		'tweet_id',
		'user_ip',
		'spam',
		'fiction',
		'poetry',
		'use',
		'event',
		'disaster',
		'personal',
		'eyewitness',
		'secondhand',
		'breaking',
		'informative',
		'submit',
	].forEach(property => {
		if (typeof data[property] !== 'undefined') {
			columns.push(property);
			values .push(`$${i}`);
			updates.push(`${property}=$${i}`);
			params .push(data[property]);
			i++;
		}
	});

	columns = columns.join(',');
	values  = values.join(',');
	updates = updates.join(',');

	await pgClient.query(`
		INSERT INTO tweet_votes (${columns})
		VALUES (${values})
		ON CONFLICT (tweet_id, user_ip)
		DO UPDATE
		SET ${updates}
	`, params);

	if (typeof data.disaster !== 'undefined')
	{
		await pgClient.query(`
			INSERT INTO tweet_properties (tweet_id, crowdflower, random_forest_train)
			VALUES ($1, $2, TRUE)
			ON CONFLICT (tweet_id)
			DO UPDATE
			SET random_forest_train=TRUE
		`, [
			data.tweet_id,
			data.disaster,
		]);
	}

	res.send('success');
});

const PORT=3000;
app.listen(PORT, err => {
	console.log(`Listening on port ${PORT}`);
});
