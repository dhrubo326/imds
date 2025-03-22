#!/usr/bin/env python3
import socket
import struct
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration parameters for the load test.
SERVER_HOST = '192.168.0.108'
SERVER_PORT = 6677
NUM_CONNECTIONS = 1000       # Total concurrent connections to simulate.
REQUESTS_PER_CONNECTION = 50 # Number of requests each connection will send.

# Protocol constants (should match your server)
MAX_MSG = 4096
MAX_ARGS = 1024

def recvall(sock, n):
    """Receive exactly n bytes from the socket."""
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed unexpectedly")
        data += chunk
    return data

def build_request(tokens):
    """
    Build a request message from a list of tokens (strings) using the protocol.
    Format:
      [4 bytes] Number of tokens (big-endian unsigned int)
      For each token:
         [4 bytes] length (big-endian unsigned int)
         [N bytes] UTF-8 encoded token
    """
    req = struct.pack('!I', len(tokens))
    for token in tokens:
        token_bytes = token.encode('utf-8')
        req += struct.pack('!I', len(token_bytes)) + token_bytes
    return req

def send_request(sock, request_bytes):
    """Send the request and receive the response."""
    sock.sendall(request_bytes)
    outer_header = recvall(sock, 4)
    total_length = struct.unpack('!I', outer_header)[0]
    response_body = recvall(sock, total_length)
    status = struct.unpack('!I', response_body[:4])[0]
    payload = response_body[4:]
    return status, payload.decode('utf-8', errors='replace')

def client_task(task_id):
    """
    Client function that opens a connection, sends several requests,
    and returns timing and error metrics.
    """
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT)) as sock:
            latencies = []
            successes = 0
            # For example, we'll alternate between a SET and GET command.
            for i in range(REQUESTS_PER_CONNECTION):
                # For demonstration, let’s alternate commands.
                if i % 2 == 0:
                    tokens = ["set", f"key{task_id}_{i}", f"value{task_id}_{i}"]
                else:
                    tokens = ["get", f"key{task_id}_{i-1}"]
                request_bytes = build_request(tokens)
                start = time.time()
                try:
                    status, response = send_request(sock, request_bytes)
                    end = time.time()
                    latencies.append(end - start)
                    # Consider a response successful if status is RES_OK (0) or RES_NX (1)
                    if status in (0, 1):
                        successes += 1
                except Exception as e:
                    print(f"Task {task_id} error: {e}")
            return (successes, sum(latencies) / len(latencies) if latencies else 0)
    except Exception as e:
        print(f"Task {task_id} connection error: {e}")
        return (0, 0)

def run_load_test():
    total_success = 0
    total_latency = 0.0
    tasks = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(client_task, task_id) for task_id in range(NUM_CONNECTIONS)]
        for future in as_completed(futures):
            successes, avg_latency = future.result()
            total_success += successes
            total_latency += avg_latency
            
    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Total successful responses: {total_success}")
    print(f"Average latency per request (across all connections): {total_latency/NUM_CONNECTIONS:.4f} seconds")

if __name__ == '__main__':
    run_load_test()
