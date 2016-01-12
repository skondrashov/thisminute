#!/usr/bin/env php
<?php
require "vendor/autoload.php";
require "lib/Consumer.php";

use Fennb\Phirehose\OauthPhirehose;

$c = new Consumer('447957969-OWZYty1k63bo2i3lan2ZaUEdWZ3KtFXofZqwTBnj', 'Xu8ywbeiaekJsqrZjktEam7hNQJoSxT8RJ7SFupQ57fvV', Phirehose::METHOD_FILTER);

$c->db = new mysqli("localhost", "archivist", "DtTJLVxZ9pZEBDpY", "NYC");

$c->setLocations([[-74.5, 40, -73.5, 41]]);

$c->consume();
