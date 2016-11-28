#!/usr/bin/env php
<?php
require_once "phirehose/lib/OauthPhirehose.php";
require_once "Consumer.php";

use Fennb\Phirehose\OauthPhirehose;

$config = parse_ini_file("/srv/config/daemons.ini", true);

define('TWITTER_CONSUMER_KEY',    file_get_contents('/srv/auth/twitter/consumer_key'));
define('TWITTER_CONSUMER_SECRET', file_get_contents('/srv/auth/twitter/consumer_secret'));

$c = new Consumer(file_get_contents('/srv/auth/twitter/access_token'), file_get_contents('/srv/auth/twitter/access_token_secret'), Phirehose::METHOD_FILTER);

$c->setLocations([[$config['grid']['west'], $config['grid']['south'], $config['grid']['east'], $config['grid']['north']]]);

$c->consume();
