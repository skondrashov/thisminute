<?php
define('TIME_GRANULARITY', 600);

// daemon periods have case-insensitive definitions to avoid complications in the daemon template
define('STATISTICIAN_PERIOD', 600, true);
define('PERICOG_PERIOD',      30,  true);
define('CARTOGRAPHER_PERIOD', 30,  true);

// archivist
// distances between boundaries should be multiples of the heatmap resolution
// ie ((AWB - AEB) % AHR) === 0
// if not, part of the heatmap won't be generated
const ARCHIVIST_WEST_BOUNDARY      = -74.5;
const ARCHIVIST_EAST_BOUNDARY      = -73.5;
const ARCHIVIST_SOUTH_BOUNDARY     = 40;
const ARCHIVIST_NORTH_BOUNDARY     = 41;
const ARCHIVIST_HEATMAP_RESOLUTION = 0.1;

// statistician
const STATISTICIAN_RECALL_SCOPE = 172800; // 172800 seconds == 48 hours

// pericog
const PERICOG_NEW_WORD_THRESHOLD      = 10;
const PERICOG_RECORDED_WORD_THRESHOLD = 20;

// cartographer
const CARTOGRAPHER_LOOKBACK  = 3600;  // 3600 seconds  == 1 hour
const CARTOGRAPHER_LOOKAHEAD = 18000; // 18000 seconds == 5 hours
