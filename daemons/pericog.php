#!/usr/bin/env php
<?php
const DAEMON = 'pericog';

function daemon($db, $last_runtime, $config)
{
	shell_exec("/srv/daemons/pericog " . $last_runtime);
}

require 'lib/daemons/template.php';
