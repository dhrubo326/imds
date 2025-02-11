"""An In-memory key–value server."""
import socket
import struct
import selectors

# Protocol and buffer constants
MAX_MSG = 4096          # Maximum allowed payload size per string
MAX_ARGS = 1024         # Maximum number of arguments in a request

sel = selectors.DefaultSelector()

# In-memory key–value store (will be replaced it later)
db = {}

# Response status codes
RES_OK = 0     # Operation succeeded
RES_NX = 1     # Key not found
RES_ERR = 2    # Error / unrecognized command

# ----- Application Command Handlers ----- #

def set_value(key, value):
    db[key] = value
    return 'OK'

def get_value(key):
    return db.get(key, "(nil)")

def delete_key(key):
    if key in db:
        del db[key]
        return 'OK'
    return '(nil)'

def process_kv_command(args):
    """
    Process a key–value command given as a list of strings.
    Supported commands:
      - get key
      - set key value
      - del key
    Returns a tuple (status, response_string).
    """
    if not args:
        return (RES_ERR, "Unknown command")
    cmd = args[0].lower()
    if cmd == 'get':
        if len(args) != 2:
            return (RES_ERR, "ERR wrong number of arguments")
        val = get_value(args[1])
        if val == "(nil)":
            return (RES_NX, "")
        return (RES_OK, val)
    elif cmd == 'set':
        if len(args) != 3:
            return (RES_ERR, "ERR wrong number of arguments")
        set_value(args[1], args[2])
        return (RES_OK, "OK")
    elif cmd == 'del':
        if len(args) != 2:
            return (RES_ERR, "ERR wrong number of arguments")
        delete_key(args[1])
        return (RES_OK, "OK")
    else:
        return (RES_ERR, "ERR unknown command")

# ----- Protocol Parsing ----- #

def parse_kv_request(buf):
    """
    Attempt to parse a KV request from the beginning of buf.
    Format:
      [4 bytes] nstr (number of strings, big-endian unsigned int)
      For each string:
         [4 bytes] length of the string (big-endian unsigned int)
         [N bytes] the string (UTF-8 encoded)
    Returns (args, bytes_consumed) if a complete request is available, or (None, 0) otherwise.
    """
    if len(buf) < 4:
        return None, 0
    nstr = struct.unpack('!I', buf[:4])[0]
    if nstr > MAX_ARGS:
        print("Too many arguments in request:", nstr)
        return None, 0
    pos = 4
    args = []
    for _ in range(nstr):
        if len(buf) < pos + 4:
            return None, 0
        arg_len = struct.unpack('!I', buf[pos:pos+4])[0]
        pos += 4
        if len(buf) < pos + arg_len:
            return None, 0
        try:
            arg = buf[pos:pos+arg_len].decode('utf-8')
        except UnicodeDecodeError as e:
            print("Decode error:", e)
            return None, 0
        args.append(arg)
        pos += arg_len
    return args, pos

# ----- Connection Class ----- #

class Connection:
    """
    Represents a client connection.
    
    Maintains per-connection buffers:
      - recv_buffer: a bytearray to accumulate incoming data.
      - send_buffer: a bytearray for outgoing response data.
    
    Implements the KV protocol:
      Request: a list of strings (each preceded by its 4-byte length) with a 4-byte count.
      Response: an outer 4-byte header (total response length) followed by an inner response:
                4 bytes for a status code plus a UTF-8 encoded payload.
    """
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.recv_buffer = bytearray()
        self.send_buffer = bytearray()

    def process_read(self):
        """Read data from the socket and process complete requests."""
        try:
            data = self.sock.recv(MAX_MSG)
        except BlockingIOError:
            return True  # No data available now.
        except Exception as e:
            print(f"Error reading from {self.addr}: {e}")
            return False

        if data:
            self.recv_buffer.extend(data)
            while True:
                parsed, consumed = parse_kv_request(self.recv_buffer)
                if parsed is None:
                    break  # Incomplete request; wait for more data.
                # Remove processed data.
                del self.recv_buffer[:consumed]
                # Process the command.
                status, resp_str = process_kv_command(parsed)
                resp_bytes = resp_str.encode('utf-8')
                inner_resp = struct.pack('!I', status) + resp_bytes
                outer_header = struct.pack('!I', len(inner_resp))
                full_response = outer_header + inner_resp
                self.send_buffer.extend(full_response)
        else:
            # recv() returned empty data; connection closed by client.
            return False
        return True

    def process_write(self):
        """Write as much of the send_buffer as possible to the socket."""
        if self.send_buffer:
            try:
                sent = self.sock.send(self.send_buffer)
                del self.send_buffer[:sent]
            except BlockingIOError:
                return True  # Try again later.
            except Exception as e:
                print(f"Error writing to {self.addr}: {e}")
                return False
        return True

    def process_events(self, mask):
        """Process read/write events based on the mask."""
        if mask & selectors.EVENT_READ:
            if not self.process_read():
                return False
        if mask & selectors.EVENT_WRITE:
            if not self.process_write():
                return False
        return True

# ----- Event Loop Callbacks ----- #

def service_connection(conn, mask):
    """
    Callback for a client connection.
    Processes events and then updates the selector registration based on whether
    there's pending data to send.
    """
    if not conn.process_events(mask):
        print(f"Closing connection to {conn.addr}")
        sel.unregister(conn.sock)
        conn.sock.close()
    else:
        # If there is pending data, register for write events.
        events = selectors.EVENT_READ
        if conn.send_buffer:
            events |= selectors.EVENT_WRITE
        sel.modify(conn.sock, events, data=conn)

def accept_connection(server_sock, mask):
    """Accept a new connection and register it for Readiness API."""
    try:
        client_sock, client_addr = server_sock.accept()
        print(f"Accepted connection from {client_addr}")
        client_sock.setblocking(False)
        conn = Connection(client_sock, client_addr)
        sel.register(client_sock, selectors.EVENT_READ, data=conn) 
    except Exception as e:
        print("Error accepting connection:", e)

# ----- Main  ----- #

def start_server(host_ip='192.168.0.108', port=6677):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host_ip, port))
    server_sock.listen()
    print(f"Server started on {host_ip}:{port}")
    server_sock.setblocking(False)
    sel.register(server_sock, selectors.EVENT_READ, data=None)
    #Event Loop
    try:
        while True:
            events = sel.select(timeout = 1)
            if not events:
                    # We will handle background jobs later
                    continue
            for key, mask in events:
                if key.data is None:
                    accept_connection(key.fileobj, mask)
                else:
                    service_connection(key.data, mask)
    except KeyboardInterrupt:
        print("Event loop interrupted; exiting.")
    finally:
        sel.close()
        server_sock.close()

if __name__ == '__main__':
    start_server()
