import threading
import struct
import select
import os
import openziti
import socket
import sys

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
        print(f"SOCKS5 server listening on {self.host}:{self.port}")
        
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"Connection from {client_address}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        try:
            if not self.socks5_handshake(client_socket):
                return
            self.socks5_connect(client_socket)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()

    def socks5_handshake(self, client_socket):
        version, n_methods = struct.unpack("!BB", client_socket.recv(2))
        assert version == 5
        
        methods = client_socket.recv(n_methods)
        
        if self.username and self.password:
            if 2 not in methods:
                client_socket.sendall(struct.pack("!BB", 5, 0xFF))
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
                return False
            client_socket.sendall(struct.pack("!BB", 1, 0))
        else:
            client_socket.sendall(struct.pack("!BB", 5, 0))

        return True

    def socks5_connect(self, client_socket):
        openziti.monkeypatch()
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

        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((address, port))

        client_socket.sendall(struct.pack("!BBBB", 5, 0, 0, 1) + socket.inet_aton("0.0.0.0") + struct.pack("!H", 0))

        self.relay_traffic(client_socket, remote_socket)

    def relay_traffic(self, client_socket, remote_socket):
        openziti.monkeypatch()
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
            print(f"Relay error: {e}")
        finally:
            client_socket.close()
            remote_socket.close()

def validate_env():
    host = os.getenv("PROXY_HOST")
    port = os.getenv("PROXY_PORT")
    username = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    
    if not host:
        print("Error: PROXY_HOST environment variable is missing.")
        sys.exit(1)
    
    try:
        port = int(port)
        if not (0 < port < 65536):
            raise ValueError
    except (ValueError, TypeError):
        print("Error: PROXY_PORT must be a valid port number (1-65535).")
        sys.exit(1)
    
    return host, port, username, password

if __name__ == "__main__":
    PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD = validate_env()

    server = Socks5Server(PROXY_HOST=PROXY_HOST, PROXY_PORT=PROXY_PORT, PROXY_USERNAME=PROXY_USERNAME, PROXY_PASSWORD=PROXY_PASSWORD)
    server.start()