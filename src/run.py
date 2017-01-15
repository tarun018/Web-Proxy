#!/usr/bin/python

import sys

from server import WebProxyServer

if __name__ == "__main__":
    port=8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    listen_address = "127.0.0.1"
    if len(sys.argv) > 2:
        listen_address = int(sys.argv[2])
    print "Listening on " + str(port) + " ..."
    server = WebProxyServer(port=port, listen_address=listen_address, debug=True, cache=True)
    # server.set_parent_proxy("proxy.iiit.ac.in", 8080)
    while 1:
        server.listen_for_request()
    server.close()

