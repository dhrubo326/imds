import socket
import struct

def recvall(sock, n):
    """
    Receive exactly n bytes from the socket.
    Raises ConnectionError if the connection is closed before n bytes are received.
    """
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket connection closed unexpectedly")
        data += chunk
    return data

def build_request(tokens):
    """
    Build a request message from a list of tokens (strings) using the KV protocol.
    Format:
      [4 bytes] Number of tokens (big-endian unsigned int)
      For each token:
         [4 bytes] Length of token (big-endian unsigned int)
         [N bytes] UTF-8 encoded token
    """
    n = len(tokens)
    req = struct.pack('!I', n)
    for token in tokens:
        token_bytes = token.encode('utf-8')
        token_len = len(token_bytes)
        req += struct.pack('!I', token_len) + token_bytes
    return req

def send_request(sock, request_bytes):
    """
    Sends the entire request to the server and receives the response.
    Response format:
      [4 bytes] Total length of the response body (big-endian unsigned int)
      [4 bytes] Status code (big-endian unsigned int)
      [Remaining bytes] Response payload (UTF-8 encoded)
    Returns a tuple (status, response_payload_string).
    """
    sock.sendall(request_bytes)
    
    # Receive the outer header to determine the response body length.
    outer_header = recvall(sock, 4)
    total_length = struct.unpack('!I', outer_header)[0]
    
    # Read the complete response body.
    response_body = recvall(sock, total_length)
    
    # Extract the status code (first 4 bytes) and payload.
    status = struct.unpack('!I', response_body[:4])[0]
    payload = response_body[4:]
    return status, payload.decode('utf-8', errors='replace')

def main():
    host = '192.168.0.108'  # Ensure this matches your server's IP
    port = 6677
    try:
        with socket.create_connection((host, port)) as sock:
            print(f"Connected to server at {host}:{port}")
            while True:
                user_input = input(
                    "Enter command (e.g., 'get key', 'set key value', 'del key', or 'exit' to quit): "
                ).strip()
                if user_input.lower() == "exit":
                    print("Exiting client.")
                    break
                if not user_input:
                    continue  # Skip empty input
                # Split the user input into tokens
                tokens = user_input.split()
                # Build the request message in the proper protocol format.
                request_bytes = build_request(tokens)
                try:
                    status, response = send_request(sock, request_bytes)
                    print(f"Status: {status}, Response: {response}")
                except Exception as e:
                    print(f"Error during request/response: {e}")
                    break
    except Exception as e:
        print(f"Could not connect to server: {e}")

if __name__ == '__main__':
    main()
