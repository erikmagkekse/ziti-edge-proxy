import threading
import struct
import select
import os
import openziti
import socket
import sys
import logging
import base64

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class Socks5Server:
    def __init__(self, PROXY_HOST='0.0.0.0', PROXY_PORT=1080, PROXY_USERNAME=None, PROXY_PASSWORD=None):
        self.host = PROXY_HOST
        self.port = PROXY_PORT
        self.username = PROXY_USERNAME
        self.password = PROXY_PASSWORD
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"SOCKS5 server listening on {self.host}:{self.port}")
        
        while True:
            client_socket, client_address = self.server_socket.accept()
            logging.info(f"SOCKS5 Connection from {client_address}")
            threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()

    def handle_client(self, client_socket, client_address):
        try:
            if not self.socks5_handshake(client_socket):
                return
            self.socks5_connect(client_socket)
        except Exception as e:
            logging.error(f"Error handling SOCKS5 client {client_address}: {e}")
        finally:
            client_socket.close()
            logging.info(f"SOCKS5 Connection closed: {client_address}")

    def socks5_handshake(self, client_socket):
        try:
            version, n_methods = struct.unpack("!BB", client_socket.recv(2))
            assert version == 5
            
            methods = client_socket.recv(n_methods)
            
            if self.username and self.password:
                if 2 not in methods:
                    client_socket.sendall(struct.pack("!BB", 5, 0xFF))
                    logging.warning("No supported authentication methods.")
                    return False
                client_socket.sendall(struct.pack("!BB", 5, 2))
                
                version = struct.unpack("!B", client_socket.recv(1))[0]
                if version != 1:
                    return False
                
                ulen = struct.unpack("!B", client_socket.recv(1))[0]
                username = client_socket.recv(ulen).decode()
                plen = struct.unpack("!B", client_socket.recv(1))[0]
                password = client_socket.recv(plen).decode()

                if username != self.username or password != self.password:
                    client_socket.sendall(struct.pack("!BB", 1, 1))
                    logging.warning("Authentication failed.")
                    return False
                client_socket.sendall(struct.pack("!BB", 1, 0))
            else:
                client_socket.sendall(struct.pack("!BB", 5, 0))

            return True
        except Exception as e:
            logging.error(f"Error during SOCKS5 handshake: {e}")
            return False

    def socks5_connect(self, client_socket):
        openziti.monkeypatch()
        try:
            version, cmd, _, addr_type = struct.unpack("!BBBB", client_socket.recv(4))
            assert version == 5
            
            if cmd != 1:
                client_socket.sendall(struct.pack("!BBBBIH", 5, 7, 0, 1, 0, 0))
                raise ValueError("Only CONNECT command is supported")

            if addr_type == 1:
                address = socket.inet_ntoa(client_socket.recv(4))
            elif addr_type == 3:
                domain_length = struct.unpack("!B", client_socket.recv(1))[0]
                address = client_socket.recv(domain_length).decode("utf-8")
            else:
                raise ValueError("Unsupported address type")

            port = struct.unpack("!H", client_socket.recv(2))[0]

            logging.info(f"Connecting to {address}:{port}")
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((address, port))

            client_socket.sendall(struct.pack("!BBBB", 5, 0, 0, 1) + socket.inet_aton("0.0.0.0") + struct.pack("!H", 0))

            self.relay_traffic(client_socket, remote_socket)
        except Exception as e:
            logging.error(f"Error during SOCKS5 connect: {e}")

    def relay_traffic(self, client_socket, remote_socket):
        try:
            while True:
                ready_sockets, _, _ = select.select([client_socket, remote_socket], [], [])
                for sock in ready_sockets:
                    data = sock.recv(4096)
                    if not data:
                        return
                    if sock is client_socket:
                        remote_socket.sendall(data)
                    else:
                        client_socket.sendall(data)
        except Exception as e:
            logging.error(f"Relay error: {e}")
        finally:
            client_socket.close()
            remote_socket.close()

class HttpProxyServer:
    def __init__(self, PROXY_HOST='0.0.0.0', PROXY_PORT=8080, PROXY_USERNAME=None, PROXY_PASSWORD=None):
        self.host = PROXY_HOST
        self.port = PROXY_PORT
        self.username = PROXY_USERNAME
        self.password = PROXY_PASSWORD
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"HTTP proxy server listening on {self.host}:{self.port}")
        
        while True:
            client_socket, client_address = self.server_socket.accept()
            logging.info(f"HTTP Connection from {client_address}")
            threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()

    def handle_client(self, client_socket, client_address):
        try:
            request = client_socket.recv(4096).decode()
            headers = request.split("\r\n")
            if self.username and self.password:
                auth_header = [h for h in headers if h.startswith("Proxy-Authorization:")]
                if not auth_header or not self.authenticate(auth_header[0]):
                    client_socket.sendall(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
                    logging.warning("HTTP authentication failed.")
                    return

            first_line = headers[0].split()
            method, url, _ = first_line
            logging.info(f"Requested URL: {url}")
            target_host, target_port = self.parse_url(url)

            openziti.monkeypatch()
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((target_host, target_port))

            if method == "CONNECT":
                client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            else:
                remote_socket.sendall(request.encode())

            self.relay_traffic(client_socket, remote_socket)
        except Exception as e:
            logging.error(f"HTTP Proxy error for {client_address}: {e}")
        finally:
            client_socket.close()
            logging.info(f"HTTP Connection closed: {client_address}")

    def authenticate(self, auth_header):
        try:
            auth_value = auth_header.split()[2]
            credentials = f"{self.username}:{self.password}".encode()
            return auth_value == base64.b64encode(credentials).decode()
        except Exception as e:
            logging.error(f"Error authenticating: {e}")
            return False

    def parse_url(self, url):
        if "://" in url:
            url = url.split("://")[1]
        if ":" in url:
            host, port = url.split(":")
            return host, int(port.split("/")[0])
        return url.split("/")[0], 80

    def relay_traffic(self, client_socket, remote_socket):
        try:
            while True:
                ready_sockets, _, _ = select.select([client_socket, remote_socket], [], [])
                for sock in ready_sockets:
                    data = sock.recv(4096)
                    if not data:
                        return
                    if sock is client_socket:
                        remote_socket.sendall(data)
                    else:
                        client_socket.sendall(data)
        except Exception as e:
            logging.error(f"Relay error: {e}")
        finally:
            client_socket.close()
            remote_socket.close()

def validate_env():
    socks_host = os.getenv("PROXY_HOST")
    socks_port = os.getenv("SOCKS_PORT")
    http_port = os.getenv("HTTP_PORT")
    username = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    socks_enabled = os.getenv("SOCKS_ENABLED", "false").lower() == "true"
    http_enabled = os.getenv("HTTP_ENABLED", "false").lower() == "true"
    
    if not socks_host:
        logging.error("PROXY_HOST environment variable is missing.")
        sys.exit(1)
    
    try:
        socks_port = int(socks_port)
        http_port = int(http_port)
        if not (0 < socks_port < 65536) or not (0 < http_port < 65536):
            raise ValueError
    except (ValueError, TypeError):
        logging.error("Ports must be valid port numbers (1-65535).")
        sys.exit(1)
    
    return socks_host, socks_port, http_port, username, password, socks_enabled, http_enabled

if __name__ == "__main__":
    PROXY_HOST, SOCKS_PORT, HTTP_PORT, PROXY_USERNAME, PROXY_PASSWORD, SOCKS_ENABLED, HTTP_ENABLED = validate_env()

    if SOCKS_ENABLED:
        socks_server = Socks5Server(PROXY_HOST=PROXY_HOST, PROXY_PORT=SOCKS_PORT, PROXY_USERNAME=PROXY_USERNAME, PROXY_PASSWORD=PROXY_PASSWORD)
        threading.Thread(target=socks_server.start).start()

    if HTTP_ENABLED:
        http_server = HttpProxyServer(PROXY_HOST=PROXY_HOST, PROXY_PORT=HTTP_PORT, PROXY_USERNAME=PROXY_USERNAME, PROXY_PASSWORD=PROXY_PASSWORD)
        threading.Thread(target=http_server.start).start()
