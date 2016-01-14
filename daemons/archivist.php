#!/usr/bin/env php
<?php
require "vendor/autoload.php";
require "lib/Consumer.php";

use Fennb\Phirehose\OauthPhirehose;

define('TWITTER_CONSUMER_KEY',    file_get_contents('/srv/auth/twitter/consumer_key'));
define('TWITTER_CONSUMER_SECRET', file_get_contents('/srv/auth/twitter/consumer_secret'));

$c = new Consumer(file_get_contents('/srv/auth/twitter/access_token'), file_get_contents('/srv/auth/twitter/access_token_secret'), Phirehose::METHOD_FILTER);

$db = new mysqli("localhost", "archivist", file_get_contents("/srv/auth/daemons/archivist.pw"), "NYC");

$c->setLocations([[-74.5, 40, -73.5, 41]]);

$c->consume();
