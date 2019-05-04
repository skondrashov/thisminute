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

const PORT=3000;
app.listen(PORT, err => {
	console.log(`Listening on port ${PORT}`);
});
