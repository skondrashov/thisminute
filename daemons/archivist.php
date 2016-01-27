#!/usr/bin/env php
<?php
require "vendor/autoload.php";
require "lib/Consumer.php";
require 'lib/stats.php';

use Fennb\Phirehose\OauthPhirehose;

define('TWITTER_CONSUMER_KEY',    file_get_contents('/srv/auth/twitter/consumer_key'));
define('TWITTER_CONSUMER_SECRET', file_get_contents('/srv/auth/twitter/consumer_secret'));

$c = new Consumer(file_get_contents('/srv/auth/twitter/access_token'), file_get_contents('/srv/auth/twitter/access_token_secret'), Phirehose::METHOD_FILTER);

$c->db = new mysqli("localhost", "archivist", file_get_contents("/srv/auth/daemons/archivist.pw"), "NYC");

$c->setLocations([[ARCHIVIST_WEST_BOUNDARY, ARCHIVIST_SOUTH_BOUNDARY, ARCHIVIST_EAST_BOUNDARY, ARCHIVIST_NORTH_BOUNDARY]]);

$c->consume();
