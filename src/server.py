"""
Author: Tarun Gupta
ID: 201403002
"""

import socket
import time
import threading


class WebProxyServer:
    """Intercept proxy request from clients"""

    cache_responses = {}

    def __init__(self, port=8080, listen_address="127.0.0.1", debug=False, cache=True):
        self.port = port
        self.listen_address = listen_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.socket.bind((self.listen_address, self.port))
        # Number of requests to put into queue, as the chrome/client can send many requests at a
        # time, I am having this value to be large.
        self.socket.listen(5)
        self.size = 8192
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.parent_proxy = False
        self.debug = debug
        self.cache = cache

    def set_parent_proxy(self, host, port):
        self.parent_proxy = True
        self.parent_proxy_host = host
        self.parent_proxy_port = port
        self.parent_proxy_ip = None

    def receive_complete_request(self, open_socket, timeout=1.0):
        open_socket.setblocking(0)
        parsed_headers = {}
        headers_expected = True
        data = []
        begin = time.time()
        while 1:
            if len(data) > 0 and time.time() - begin > timeout/3:
                break
            elif len(data) is 0 and time.time() - begin > timeout:
                break

            try:
                incoming_data = open_socket.recv(self.size)
                if incoming_data:
                    data.append(incoming_data)

                    # Parsing the headers
                    if headers_expected:
                        for line in incoming_data.split('\n'):
                            line = line.strip()
                            if line is "":
                                headers_expected = False
                                break
                            line = line.split(': ')
                            key = line[0].strip()
                            value = ''.join(line[1:]).strip()
                            if key is not "":
                                parsed_headers[key.lower()] = value

                    # Reset the waiting timeout
                    begin = time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        return ''.join(data), parsed_headers

    def fetch_parent_proxy(self, request):
        # Opening a new socket and connecting to Parent proxy (resolving the parent proxy only once)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        if not self.parent_proxy_ip:
            self.parent_proxy_ip = socket.gethostbyname(self.parent_proxy_host)
        client_socket.connect((self.parent_proxy_ip, self.parent_proxy_port))

        # Sending request to parent proxy
        client_socket.send(request)
        return_data = self.receive_complete_request(client_socket)
        client_socket.close()
        return return_data

    def fetch_as_client(self, request, parsed_request):
        # Open a new socket for fetching the URL
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        # Resolving the URL to get IP (or using Host directly if present
        host_name = parsed_request['URL'].split("//")[-1].split("/")[0].strip()
        if 'Host' in parsed_request:
            host_name = parsed_request['Host']
        connect_port = 80
        if ":" in host_name:
            host_name = host_name.split(':')
            connect_port = int(host_name[1])
            host_name = host_name[0]
        try:
            resolved_ip = socket.gethostbyname(host_name)
        except:
            return {}, {}

        # Making the request
        client_socket.connect((resolved_ip, connect_port))
        client_socket.send(request)
        return_data = self.receive_complete_request(client_socket)
        client_socket.close()
        return return_data

    @staticmethod
    def can_cache_request(headers):
        if len(headers) == 0:
            # Something bad happened with request, lets not cache it.
            return False
        if 'http/1.1 200 ok' not in headers:
            return False
        if 'cache-control' in headers:
            value = headers['cache-control']
            if "private" in value or "no-cache" in value:
                return False
        if 'pragma' in headers:
            value = headers['pragma']
            if "private" in value or "no-cache" in value:
                return False
        return True

    @staticmethod
    def cache_timeout_request(headers):
        # not implemented/reading Expires, Last_modified, etc.
        # If needed it's implementation can come here.
        return 0

    def serve_request(self, request, parsed_request):
        # Check cache, if not fetch and cache
        if parsed_request['URL'] in self.cache_responses:
            self.debug_statement('Found in cache for ' + parsed_request['URL'])
            return self.cache_responses[parsed_request['URL']]
        if self.parent_proxy:
            response, parsed_headers = self.fetch_parent_proxy(request)
        else:
            response, parsed_headers = self.fetch_as_client(request, parsed_request)

        if self.can_cache_request(parsed_headers):
            # timeout = self.cache_timeout_request(parsed_headers)
            if self.cache:
                self.debug_statement('Adding to cache ' + parsed_request['URL'])
                self.cache_responses[parsed_request['URL']] = response
        else:
            self.debug_statement('Skipping cache due to header for ' + parsed_request['URL'])
        return response

    @staticmethod
    def parse_request(request):
        parsed_data = {'Valid': True}
        request = request.split('\n')
        first_line = request[0].split(' ')
        # Checking if the first line contains at least two variables, i.e. {GET,POST} URL
        if not len(first_line) >= 2:
            parsed_data['Valid'] = False
        else:
            parsed_data['Type'] = first_line[0]
            parsed_data['URL'] = first_line[1]
            for var in request[1:]:
                temp_var = var.split(':')
                key = temp_var[0].strip()
                value = ' '.join(temp_var[1:]).strip()
                if key is not "":
                    parsed_data[key] = value
                pass
        return parsed_data

    def debug_statement(self, message):
        if self.debug:
            print message

    @staticmethod
    def clean_unwanted_headers(request):
        request = request.split('\r\n')
        clean_request = []
        for line in request:
            if not line.lower().startswith('if-'):
                clean_request.append(line)
        return '\r\n'.join(clean_request)

    def listen_for_request_threaded(self, client, address):
        request = client.recv(self.size)
        # request = self.clean_unwanted_headers(request)
        parsed_request = self.parse_request(request)

        if parsed_request['Valid']:
            self.debug_statement('Fetching ' + parsed_request['URL'])
            response = self.serve_request(request, parsed_request)
            client.send(str(response))

    def listen_for_request(self):
        client, address = self.socket.accept()
        client.settimeout(10)
        threading.Thread(target=self.listen_for_request_threaded, args=(client,address)).start()

    def close(self):
        self.socket.close()

