#!/usr/bin/env php
<?php
const DAEMON = 'pericog';

function daemon($db, $last_runtime, $config)
{
	shell_exec("/srv/bin/pericog -l $last_runtime -o");
}

require 'lib/daemons/template.php';
