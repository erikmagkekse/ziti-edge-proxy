import threading
import struct
import select
import os
import openziti
import socket
import sys
import logging
import base64
import time

# Set ZITI_LOG for SDK debug output if not already set
if not os.getenv("ZITI_LOG"):
    os.environ["ZITI_LOG"] = "3"  # INFO level, use 6 for TRACE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def recv_all(sock, n):
    """Receive exactly n bytes or raise ConnectionError"""
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed by client")
        data += chunk
    return data


class Socks5Server:
    def __init__(self, PROXY_HOST='0.0.0.0', PROXY_PORT=1080, PROXY_USERNAME=None, PROXY_PASSWORD=None):
        self.host = PROXY_HOST
        self.port = PROXY_PORT
        self.username = PROXY_USERNAME
        self.password = PROXY_PASSWORD
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(128)  # Increased backlog for parallel connections
        logging.info(f"SOCKS5 server listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = self.server_socket.accept()
            logging.info(f"SOCKS5 Connection from {client_address}")
            threading.Thread(target=self.handle_client, args=(client_socket, client_address), daemon=True).start()

    def handle_client(self, client_socket, client_address):
        try:
            # Immediately set socket options to reduce latency
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

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
            # Set a short timeout to detect dead connections quickly
            client_socket.settimeout(5.0)

            logging.debug(f"Starting SOCKS5 handshake, reading greeting...")
            version, n_methods = struct.unpack("!BB", recv_all(client_socket, 2))
            logging.debug(f"SOCKS5 greeting received: version={version}, n_methods={n_methods}")
            assert version == 5

            methods = recv_all(client_socket, n_methods)

            if self.username and self.password:
                if 2 not in methods:
                    client_socket.sendall(struct.pack("!BB", 5, 0xFF))
                    logging.warning("No supported authentication methods.")
                    return False
                client_socket.sendall(struct.pack("!BB", 5, 2))

                version = struct.unpack("!B", recv_all(client_socket, 1))[0]
                if version != 1:
                    return False

                ulen = struct.unpack("!B", recv_all(client_socket, 1))[0]
                username = recv_all(client_socket, ulen).decode()
                plen = struct.unpack("!B", recv_all(client_socket, 1))[0]
                password = recv_all(client_socket, plen).decode()

                if username != self.username or password != self.password:
                    client_socket.sendall(struct.pack("!BB", 1, 1))
                    logging.warning("Authentication failed.")
                    return False
                client_socket.sendall(struct.pack("!BB", 1, 0))
            else:
                client_socket.sendall(struct.pack("!BB", 5, 0))

            return True
        except (ConnectionError, BrokenPipeError) as e:
            # Client disconnected during handshake - log at INFO to diagnose issues
            logging.info(f"Client disconnected during SOCKS5 handshake: {e}")
            return False
        except OSError as e:
            if e.errno in (107, 104, 32):  # ENOTCONN, ECONNRESET, EPIPE
                logging.info(f"Client connection closed during handshake (errno {e.errno}): {e}")
                return False
            logging.error(f"OS error during SOCKS5 handshake: {e}")
            return False
        except socket.timeout:
            logging.warning("SOCKS5 handshake timeout")
            return False
        except Exception as e:
            logging.error(f"Error during SOCKS5 handshake: {e}")
            return False

    def socks5_connect(self, client_socket):
        try:
            version, cmd, _, addr_type = struct.unpack("!BBBB", recv_all(client_socket, 4))
            assert version == 5

            if cmd != 1:
                client_socket.sendall(struct.pack("!BBBBIH", 5, 7, 0, 1, 0, 0))
                raise ValueError("Only CONNECT command is supported")

            if addr_type == 1:
                address = socket.inet_ntoa(recv_all(client_socket, 4))
            elif addr_type == 3:
                domain_length = struct.unpack("!B", recv_all(client_socket, 1))[0]
                address = recv_all(client_socket, domain_length).decode("utf-8")
            else:
                raise ValueError("Unsupported address type")

            port = struct.unpack("!H", recv_all(client_socket, 2))[0]

            logging.info(f"Connecting to {address}:{port}")

            # Retry logic for Ziti SDK initialization race condition
            max_retries = 3
            retry_delay = 3
            last_error = None
            remote_socket = None

            for attempt in range(max_retries):
                connect_start = time.time()
                try:
                    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote_socket.settimeout(30)  # 30 second connection timeout
                    remote_socket.connect((address, port))
                    connect_time = time.time() - connect_start
                    logging.info(f"Connected to {address}:{port} in {connect_time:.3f}s")
                    break
                except Exception as conn_err:
                    connect_time = time.time() - connect_start
                    last_error = conn_err
                    try:
                        remote_socket.close()
                    except:
                        pass
                    if attempt < max_retries - 1:
                        logging.warning(f"Connection to {address}:{port} failed (attempt {attempt + 1}/{max_retries}): {conn_err}, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                    else:
                        logging.error(f"Connection to {address}:{port} FAILED after {max_retries} attempts: {conn_err}")
                        # Send SOCKS5 connection refused reply
                        client_socket.sendall(struct.pack("!BBBBIH", 5, 5, 0, 1, 0, 0))
                        raise

            remote_socket.settimeout(None)  # Reset to blocking mode

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
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(128)  # Increased backlog for parallel connections
        logging.info(f"HTTP proxy server listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = self.server_socket.accept()
            logging.info(f"HTTP Connection from {client_address}")
            threading.Thread(target=self.handle_client, args=(client_socket, client_address), daemon=True).start()

    def handle_client(self, client_socket, client_address):
        try:
            # Immediately set socket options to reduce latency
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

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

    # Validating SOCKS port only if SOCKS_ENABLED is true
    if socks_enabled:
        try:
            socks_port = int(socks_port)
            if not (0 < socks_port < 65536):
                raise ValueError
        except (ValueError, TypeError):
            logging.error("SOCKS_PORT must be a valid port number (1-65535).")
            sys.exit(1)

    # Validating HTTP port only if HTTP_ENABLED is true
    if http_enabled:
        try:
            http_port = int(http_port)
            if not (0 < http_port < 65536):
                raise ValueError
        except (ValueError, TypeError):
            logging.error("HTTP_PORT must be a valid port number (1-65535).")
            sys.exit(1)

    return socks_host, socks_port, http_port, username, password, socks_enabled, http_enabled

if __name__ == "__main__":
    PROXY_HOST, SOCKS_PORT, HTTP_PORT, PROXY_USERNAME, PROXY_PASSWORD, SOCKS_ENABLED, HTTP_ENABLED = validate_env()

    # Create server sockets BEFORE monkeypatch (they should be regular TCP sockets)
    socks_server = None
    http_server = None
    if SOCKS_ENABLED:
        socks_server = Socks5Server(PROXY_HOST=PROXY_HOST, PROXY_PORT=SOCKS_PORT, PROXY_USERNAME=PROXY_USERNAME, PROXY_PASSWORD=PROXY_PASSWORD)
    if HTTP_ENABLED:
        http_server = HttpProxyServer(PROXY_HOST=PROXY_HOST, PROXY_PORT=HTTP_PORT, PROXY_USERNAME=PROXY_USERNAME, PROXY_PASSWORD=PROXY_PASSWORD)

    # Now monkeypatch so outgoing connections use Ziti
    openziti.monkeypatch()

    # Start servers
    if socks_server:
        threading.Thread(target=socks_server.start).start()
    if http_server:
        threading.Thread(target=http_server.start).start()
