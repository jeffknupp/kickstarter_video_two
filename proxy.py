"""An HTTP proxy that supports IPv6 as well as the HTTP CONNECT method, among
other things."""

# Standard libary imports
import socket
import thread
import select

__version__ = '0.1.0 Draft 1'
BUFLEN = 8192
VERSION = 'Python Proxy/'+__version__
HTTPVER = 'HTTP/1.1'


class ConnectionHandler(object):
    """Handles connections between the HTTP client and HTTP server."""
    def __init__(self, connection, _, timeout):
        self.client = connection
        self.client_buffer = ''
        self.timeout = timeout
        self.target = None
        self.method, self.path, self.protocol = self.get_base_header()
        if self.method == 'CONNECT':
            self.method_connect()
        elif self.method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE'):
            self.method_others()
        self.client.close()
        self.target.close()

    def get_base_header(self):
        """Return a tuple of (method, path, protocol) from the recieved
        message."""
        while 1:
            self.client_buffer += self.client.recv(BUFLEN)
            end = self.client_buffer.find('\n')
            if end != -1:
                break
        print '{}'.format(self.client_buffer[:end])
        data = (self.client_buffer[:end+1]).split()
        self.client_buffer = self.client_buffer[end+1:]
        return data

    def method_connect(self):
        """Handle HTTP CONNECT messages."""
        self._connect_target(self.path)
        self.client.send('{httpver} 200 Connection established\n'
                         'Proxy-agent: {version}\n\n'.format(
                             httpver=HTTPVER,
                             version=VERSION))
        self.client_buffer = ''
        self._read_write()

    def method_others(self):
        """Handle all non-HTTP CONNECT messages."""
        self.path = self.path[7:]
        i = self.path.find('/')
        host = self.path[:i]
        path = self.path[i:]
        self._connect_target(host)
        self.target.send('{method} {path} {protocol}\n{client_buffer}'.format(
            method=self.method,
            path=path,
            protocol=self.protocol,
            client_buffer=self.client_buffer))
        self.client_buffer = ''
        self._read_write()

    def _connect_target(self, host):
        """Create a connection to the HTTP server specified by *host*."""
        i = host.find(':')
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80
        (soc_family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family)
        self.target.connect(address)

    def _read_write(self):
        """Read data from client connection and forward to server
        connection."""
        time_out_max = self.timeout/3
        socs = [self.client, self.target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(BUFLEN)
                    if in_ is self.client:
                        out = self.target
                    else:
                        out = self.client
                    if data:
                        out.send(data)
                        count = 0
            if count == time_out_max:
                break


def start_server(host='localhost', port=8080, ipv_6=False, timeout=60,
                 handler=ConnectionHandler):
    """Start the HTTP proxy server."""
    if ipv_6:
        soc_type = socket.AF_INET6
    else:
        soc_type = socket.AF_INET
    soc = socket.socket(soc_type)
    soc.bind((host, port))
    print 'Serving on {0}:{1}.'.format(host, port)
    soc.listen(0)
    while 1:
        thread.start_new_thread(handler, soc.accept()+(timeout,))

if __name__ == '__main__':
    start_server()
