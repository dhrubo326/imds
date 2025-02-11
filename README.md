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

This project demonstrates how to build a Redis-like in-memory key-value server in Python. It is designed to be modular and maintainable, with a clear separation of concerns. The server is built with an event-driven architecture using non-blocking I/O and is capable of handling pipelined requests from multiple clients concurrently.

## Features

- **Non-Blocking I/O & Event Loop:**  
  Uses Python’s `selectors` module to manage multiple client connections concurrently in a single thread.
  
- **Custom Binary Protocol:**  
  Implements a length-prefixed protocol for both requests and responses. Requests are sent as a list of strings (with a count and length prefix for each string), and responses consist of a status code and a payload.
  
- **Basic Command Support:**  
  Supports point queries using the following commands:
  - `get <key>`
  - `set <key> <value>`
  - `del <key>`
  
- **Modular and Extensible:**  
  The code is structured to allow future expansion (e.g., adding range queries, rank queries, and cache management) without disrupting existing functionality.

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
  - Type exit to quit the client.
  
## Protocol Details

## Future Enhancements

## Project Structure

## Contributing
Contributions are welcome! Please feel free to open issues or submit pull requests for enhancements or bug fixes.

## License
This project is licensed under the MIT License.

