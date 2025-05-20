"""
server.py – Main server code for the In-Memory Key-Value Store.

This server implements a Redis-like protocol that supports point queries (GET, SET, DEL)
as well as sorted set commands (ZADD, ZRANGE, ZRANK, ZREM). It uses non-blocking I/O
with an event loop (via selectors) and a unified store that combines a hash table,
sorted sets (via a skip list), and LRU cache.
"""
import socket
import struct
import selectors

from store.unified_store import store
from store.aof import AOF

# Protocol and buffer constants
MAX_MSG = 4096          # Maximum allowed payload per string
MAX_ARGS = 1024         # Maximum number of arguments per request

sel = selectors.DefaultSelector()

# Response status codes
RES_OK = 0
RES_NX = 1
RES_ERR = 2

# AOF persistence object (global)
aof = AOF('appendonly.aof')

# ----- Application Command Handlers ----- #

def set_value(key, value):
    store.set(key, value)
    aof.append(f"SET {key} {value}")
    return 'OK'

def get_value(key):
    value = store.get(key)
    return '(nil)' if value is None else value

def delete_key(key):
    if store.get(key) is not None:
        store.delete(key)
        aof.append(f"DEL {key}")
        return 'OK'
    return '(nil)'

def set_zadd(key, score, member):
    store.process_zadd(key, score, member)
    aof.append(f"ZADD {key} {score} {member}")
    return 'OK'

def get_zrange(key, start, end):
    return store.process_zrange(key, start, end)

def get_zrank(key, member):
    value = store.process_zrank(key, member)
    return '(nil)' if value is None else str(value)

def delete_zrem(key, member):
    if store.process_zrem(key, member) is not None:
        aof.append(f"ZREM {key} {member}")
        return 'OK'
    return '(nil)'

def process_kv_command(args):
    """
    Process a key–value command given as a list of strings.
    Supported commands:
      - get key
      - set key value
      - del key
      - zadd key score member
      - zrange key start end
      - zrank key member
      - zrem key member
    Returns a tuple (status, response_string).
    """
    if not args:
        return (RES_ERR, "Unknown command")
    cmd = args[0].lower()
    if cmd == 'get':
        if len(args) != 2:
            return (RES_ERR, "ERR wrong number of arguments")
        val = get_value(args[1])
        return (RES_NX, "") if val == "(nil)" else (RES_OK, val)
    elif cmd == 'set':
        if len(args) != 3:
            return (RES_ERR, "ERR wrong number of arguments")
        set_value(args[1], args[2])
        return (RES_OK, "OK")
    elif cmd == 'del':
        if len(args) != 2:
            return (RES_ERR, "ERR wrong number of arguments")
        val = delete_key(args[1])
        return (RES_NX, "") if val == "(nil)" else (RES_OK, "OK")
    elif cmd == 'zadd':
        if len(args) != 4:
            return (RES_ERR, "ERR wrong number of arguments")
        set_name, score, member = args[1], args[2], args[3]
        # Ensure the score is converted to a float (or int if necessary)
        try:
            score = float(score)  # Convert string to number
        except ValueError:
            return (RES_ERR, "ERR score must be a number")
        set_zadd(set_name, score, member)
        return (RES_OK, "OK")
    elif cmd == 'zrange':
        if len(args) != 4:
            return (RES_ERR, "ERR wrong number of arguments")
        set_name, start_score, end_score = args[1], args[2], args[3]
        try:
            start_score = float(start_score)  # Convert string to number
            end_score = float(end_score)  # Convert string to number
        except ValueError:
            return (RES_ERR, "ERR score must be a number")
        results = get_zrange(set_name, start_score, end_score)
        if not results:
            return (RES_NX, "")
        formatted_results = [f"{score}:{member}" for score, member in results]
        return (RES_OK, ",".join(formatted_results))
    elif cmd == 'zrank':
        if len(args) != 3:
            return (RES_ERR, "ERR wrong number of arguments")
        val = get_zrank(args[1], args[2])
        return (RES_NX, "") if val == "(nil)" else (RES_OK, val)
    elif cmd == 'zrem':
        if len(args) != 3:
            return (RES_ERR, "ERR wrong number of arguments")
        val = delete_zrem(args[1], args[2])
        return (RES_NX, "") if val == "(nil)" else (RES_OK, "OK")
    else:
        return (RES_ERR, "ERR unknown command")

# ----- Protocol Parsing ----- #

def parse_kv_request(buf):
    """
    Parse a KV request from the beginning of buf.
    Format:
      [4 bytes] nstr (number of strings, big-endian unsigned int)
      For each string:
         [4 bytes] length (big-endian unsigned int)
         [N bytes] UTF-8 encoded string.
    Returns (args, bytes_consumed) if a complete request is available, else (None, 0).
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
      - recv_buffer: accumulates incoming request data.
      - send_buffer: accumulates outgoing response data.
    Implements the KV protocol.
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
            return True  # No data available right now.
        except Exception as e:
            print(f"Error reading from {self.addr}: {e}")
            return False

        if data:
            self.recv_buffer.extend(data)
            while True:
                parsed, consumed = parse_kv_request(self.recv_buffer)
                if parsed is None:
                    break
                del self.recv_buffer[:consumed]
                status, resp_str = process_kv_command(parsed)
                resp_bytes = resp_str.encode('utf-8')
                inner_resp = struct.pack('!I', status) + resp_bytes
                outer_header = struct.pack('!I', len(inner_resp))
                full_response = outer_header + inner_resp
                self.send_buffer.extend(full_response)
        else:
            return False  # Connection closed by client.
        return True

    def process_write(self):
        """Write pending response data to the socket."""
        if self.send_buffer:
            try:
                sent = self.sock.send(self.send_buffer)
                del self.send_buffer[:sent]
            except BlockingIOError:
                return True
            except Exception as e:
                print(f"Error writing to {self.addr}: {e}")
                return False
        return True

    def process_events(self, mask):
        """Process read and write events based on the event mask."""
        if mask & selectors.EVENT_READ:
            if not self.process_read():
                return False
        if mask & selectors.EVENT_WRITE:
            if not self.process_write():
                return False
        return True

# ----- Event Loop Callbacks ----- #

def service_connection(conn, mask):
    """Callback for processing events on a client connection."""
    if not conn.process_events(mask):
        print(f"Closing connection to {conn.addr}")
        sel.unregister(conn.sock)
        conn.sock.close()
    else:
        events = selectors.EVENT_READ
        if conn.send_buffer:
            events |= selectors.EVENT_WRITE
        sel.modify(conn.sock, events, data=conn)

def accept_connection(server_sock, mask):
    """Accept a new client connection and register it."""
    try:
        client_sock, client_addr = server_sock.accept()
        print(f"Accepted connection from {client_addr}")
        client_sock.setblocking(False)
        conn = Connection(client_sock, client_addr)
        sel.register(client_sock, selectors.EVENT_READ, data=conn)
    except Exception as e:
        print("Error accepting connection:", e)

# ----- Main Event Loop ----- #

def start_server(host_ip='192.168.0.108', port=6677):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host_ip, port))
    server_sock.listen()
    print(f"Server started on {host_ip}:{port}")
    server_sock.setblocking(False)
    sel.register(server_sock, selectors.EVENT_READ, data=None)

    try:
        while True:
            events = sel.select(timeout=1)
            if not events:
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
    HOST = socket.gethostbyname(socket.gethostname())
    start_server(HOST)
