Nagios cache for slow check
=============================

Cache script for nagios checks :

  * Easy to setup
  * Simple python script with unittests.
  * Cache stored in JSON file with a lot of data like runtime of the command, output, exit code, ...

Usage
------

Help :

    ./cache_check.py -d -t 20 -e 300 --help
    usage: cache_check.py [-h] -c COMMAND [-e EXPIRE] [-d] [-t TIMEOUT]
    
    optional arguments:
    -h, --help            show this help message and exit
    -c COMMAND, --command COMMAND
                          Command
    -e EXPIRE, --expire EXPIRE
                          Expire time for the cache in sec.
    -d, --debug           Enable debug mode (log in file).
    -t TIMEOUT, --timeout TIMEOUT
                          Timeout for the command in sec.
    -i INTERVAL, --interval INTERVAL
                          Minimum interval between command in sec.

Example :

    ./cache_check.py --expire 300 --timeout 30 --interval 10 --command "my_slow_check"

  * Expire : Cache expire time
  * Timeout : Background command execution timeout 
  * Interval : Minimum interval between two run command 


Behavior
---------

  - If no cache file: Run background command => UNKNOWN
  - If cache file is expired: Run background command => (UNKNOWN/CRITICAL)?
  - Else read the cache => CRITICAL/OK

In all these cases the command will not run if it is already running or if command interval not respected.


Run tests with coverage
------------------------

    nosetests -v --cover-package cache_check --with-coverage --cover-html test_cache_check.py
