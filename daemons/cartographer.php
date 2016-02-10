#!/usr/bin/env php
<?php
const DAEMON = 'cartographer';

function daemon($db, $last_runtime, $config)
{
	shell_exec("/srv/bin/cartographer " . $last_runtime);
}

require 'lib/daemons/template.php';
