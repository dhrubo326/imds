#!/usr/bin/env python3
"""
load_test_zset.py – Load test for sorted set operations (ZADD and ZRANGE).

This script uses ThreadPoolExecutor to simulate many concurrent clients.
Each client:
  - Connects to the server.
  - Uses a unique sorted set key: "ipl_<task_id>".
  - Sends a series of pipelined commands:
       * (REQUESTS_PER_CONNECTION - 1) ZADD commands (adding random score–member pairs)
       * 1 ZRANGE command to retrieve all elements with scores in a given range.
  - Measures and returns the number of successful responses and average latency per request.
  
After all tasks complete, the script prints:
  - Total time to complete all tasks.
  - Total number of successful responses.
  - Average latency per request across all connections.
"""

import socket
import struct
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# Server configuration – adjust these if needed.
SERVER_HOST = '192.168.0.108'
SERVER_PORT = 6677

# Load test parameters – adjust as needed.
NUM_CONNECTIONS = 1000          # Total concurrent client connections to simulate.
REQUESTS_PER_CONNECTION = 50   # Total requests per connection 
                              # (e.g., 10 ZADD commands and 1 ZRANGE command).

# Protocol constants (should match your server)
MAX_MSG = 4096
MAX_ARGS = 1024

# Response status codes (as defined in your server)
RES_OK = 0
RES_NX = 1
RES_ERR = 2

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
    Build a request message from a list of tokens.
    Format:
      [4 bytes] Number of tokens (big-endian unsigned int)
      For each token:
         [4 bytes] Length of token (big-endian unsigned int)
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
    Each client connects to the server and performs a series of pipelined sorted set commands.
    - Uses a unique sorted set key: "ipl_<task_id>"
    - Sends (REQUESTS_PER_CONNECTION - 1) ZADD commands with random score-member pairs.
    - Sends one final ZRANGE command (fetching members with scores between 1 and 100).
    Returns a tuple: (number_of_successful_responses, average_latency_per_request)
    """
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT)) as sock:
            key = f"ipl_{task_id}"
            successes = 0
            latencies = []
            total_requests = REQUESTS_PER_CONNECTION

            # Send ZADD commands.
            for i in range(total_requests - 1):
                score = random.randint(1, 100)
                member = f"member_{i}"
                tokens = ["zadd", key, str(score), member]
                req = build_request(tokens)
                start = time.time()
                status, resp = send_request(sock, req)
                end = time.time()
                latencies.append(end - start)
                if status in (RES_OK, RES_NX):
                    successes += 1

            # Send one ZRANGE command.
            tokens = ["zrange", key, "1", "100"]
            req = build_request(tokens)
            start = time.time()
            status, resp = send_request(sock, req)
            end = time.time()
            latencies.append(end - start)
            if status in (RES_OK, RES_NX):
                successes += 1

            total_latency = sum(latencies)
            avg_latency = total_latency / total_requests if total_requests > 0 else 0
            return successes, avg_latency
    except Exception as e:
        print(f"Task {task_id} connection error: {e}")
        return 0, 0

def run_load_test():
    total_success = 0
    total_latency = 0.0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(client_task, task_id) for task_id in range(NUM_CONNECTIONS)]
        for future in as_completed(futures):
            successes, avg_lat = future.result()
            total_success += successes
            total_latency += avg_lat

    end_time = time.time()
    total_time = end_time - start_time

    print(f"Total time: {total_time:.2f} seconds")
    print(f"Total successful responses: {total_success}")
    print(f"Average latency per request (across all connections): {total_latency/NUM_CONNECTIONS:.4f} seconds")

if __name__ == '__main__':
    run_load_test()
