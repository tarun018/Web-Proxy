HTTP Web Proxy

"""
Author: Tarun Gupta
ID: 201403002

"""
-------------

Execute as:

`python run.py 8080 127.0.0.1`

+ Works with HTTP traffic
+ Cache 200 responses
+ Listen by default to 8080, until port is passed as command line argument.
+ Listen on 127.0.0.1, until passed as command line argument.
+ Infinitely cache (not based on response header)
+ Works with telnet, curl and browser (HTTP request only)
