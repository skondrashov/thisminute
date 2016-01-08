<?php
require "vendor/autoload.php";
require "lib/Consumer.php";

use Fennb\Phirehose\OauthPhirehose;

$c = new Consumer('447957969-kz0OCtJcgRd7S5PYkT2rTxIV5sTxlT5wXku9InH4', 'RMyT6utD7tpdtvAy7RqFFLUuL3bUDLBVXO5Rwr05WcWQz', Phirehose::METHOD_FILTER);

$c->db = new mysqli("localhost", "tweets_user", "lovepotion", "NYC");

$c->setLocations([[-74.5, 40, -73.5, 41]]);

$c->consume();
