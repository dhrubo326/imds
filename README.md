#imds
# In-Memory Key-Value Store (Redis-like) in Python

This project is an educational, production-oriented in-memory key-value store implemented in Python. It mimics a subset of Redis functionality by supporting point queries (GET, SET, DEL) over a custom binary protocol. The server uses non-blocking I/O with an event loop (via Python’s `selectors` module) and per-connection buffering to handle multiple simultaneous client connections and pipelined requests efficiently.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Running the Server](#running-the-server)
  - [Running the Client](#running-the-client)
- [Protocol Details](#protocol-details)
- [Future Enhancements](#future-enhancements)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project demonstrates how to build a in-memory key-value server in Python. It is designed to be modular and maintainable, with a clear separation of concerns. The server is built with an event-driven architecture using non-blocking I/O and is capable of handling pipelined requests from multiple clients concurrently.

## Features

- **Non-Blocking I/O & Event Loop:**  
  Uses Python’s `selectors` module to manage multiple client connections concurrently in a single thread.
  
- **Custom Binary Protocol:**  
  Implements a length-prefixed protocol for both requests and responses. Requests are sent as a list of strings (with a count and length prefix for each string), and responses consist of a status code and a payload.
  
- **Command Support:**  
  Supports point queries, range queries and rank queries using the following commands:
  - `get <key>`
  - `set <key> <value>`
  - `del <key>`
  - `zadd <key> <score> <member>`
  - `zrange <key> <start_score> <end_score>`
  - `zrank <key> <member>`
  - `zrem <key> <member>`
  
- **Unified Data Structure:** 
  Combines hash table, sorted set (skip list), and LRU cache functionalities.

- **Persistence:**  
  Append-Only File (AOF) persistence for durability.

- **Modular and Extensible:**  
  Modular design allows easy future expansion (e.g., advanced range queries, LRU cache improvements) without disrupting existing functionality.

## Installation

This project requires Python 3.6 or later. No third-party packages are needed because the implementation uses only the Python standard library.

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/dhrubo326/imds.git
   cd imds
   ```
2. **(Optional) Create a Virtual Environment:**

## Usage

- **Running the Server:**  
  To start the key-value server, run:
  ```bash
  python server.py
  ```
  By default, the server listens on your local IP and port 6677. Adjust these values in the code or via command-line arguments if needed.
- **Running the Client:**  
  A sample client is provided to interact with the server. To run the client in interactive mode, execute:
  ```bash
  python client.py
  ```
  The client will prompt you for commands. You can type commands like:
  - set foo bar
  - get foo
  - del foo
  - zadd key-name score member
  - zrange key-name score_start score_end
  - zrank key-name member
  - zrem key-name member
  - Type exit to quit the client.
  
## Protocol Details
- **Request Format**
A request is sent as a binary message consisting of:
- 4 bytes: The number of tokens (nstr) (big-endian unsigned int)
- For each token:
  - 4 bytes: The length of the token (big-endian unsigned int)
  - N bytes: The token (UTF-8 encoded)
Example: The command set foo bar is sent as:
```
[ 0x00 0x00 0x00 0x03 ]  // 3 tokens
[ token1 length ][ token1 bytes ("set") ]
[ token2 length ][ token2 bytes ("foo") ]
[ token3 length ][ token3 bytes ("bar") ]
```
- **Response Format**
A response is sent as a binary message:
- 4 bytes: Outer header — total length of the inner response (big-endian unsigned int)
- Inner response:
  - 4 bytes: Status code (big-endian unsigned int). For example, 0 for success.
  - Remaining bytes: Response payload (UTF-8 encoded)
## Future Enhancements

## Project Structure
```
imds/
├── server.py           # Main server code
├── client.py           # Client for testing
├── README.md           # Project documentation
└── store/              # Package for storage–related functionality
    ├── __init__.py     # Package initializer (can be empty or expose public API)
    ├── unified_store.py  # UnifiedStore class & protocol functions (for point queries and sorted sets)
    ├── sorted_set.py   # SortedSet, SkipList, and SkipListNode classes
    ├── lru_cache.py    # LRUNode, Node (for LRU) and DoublyLinkedList classes
    └── aof.py          # AOF persistence logic
```
## Contributing
Contributions are welcome! Please feel free to open issues or submit pull requests for enhancements or bug fixes.

## License
This project is licensed under the MIT License.

