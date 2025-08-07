<?php
define('DVWA_WEB_PAGE_TO_ROOT', '/var/www/html/DVWA/');

// Fix missing $_SERVER keys in CLI
$_SERVER['HTTP_HOST'] = '127.0.0.1';
$_SERVER['SERVER_NAME'] = '127.0.0.1';
$_SERVER['SCRIPT_NAME'] = '/DVWA/setup.php';

require_once DVWA_WEB_PAGE_TO_ROOT . 'dvwa/includes/dvwaPage.inc.php';

// Set DB credentials
$_DVWA = [
    'db_server'   => '127.0.0.1',
    'db_database' => 'dvwa',
    'db_user'     => 'dvwa',
    'db_password' => 'p@ssw0rd',
    'db_port'     => 3306
];

// Run setup
include_once DVWA_WEB_PAGE_TO_ROOT . 'dvwa/includes/DBMS/MySQL.php';

echo "DVWA setup completed.\n";
