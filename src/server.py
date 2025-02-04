import socket
import threading
# Global Storage of our DB!
db = {}

def set_value(key, value):
	db[key] = value
	return 'OK'

def get_value(key):
	return db.get(key, "(nil)")

def delete_key(key):
	if key in db:
		del db[key]
		return "OK"
	return "(nil)"

def handle_command(command):
	if len(command) < 4 : return "Unknown command"
	command_parts = command.split()
	if (len(command_parts) < 2) : return "Unknown command"

	command_type = command_parts[0].lower()

	if command_type == 'get':
		if len(command_parts) != 2 : return "ERROR"
		return get_value(command_parts[1])
	elif command_type == 'set':
		if len(command_parts) != 3 : return "ERROR"
		return set_value(command_parts[1], command_parts[2])
	elif command_type == 'del':
		if len(command_parts) != 2: return "ERROR"
		return delete_key(command_parts[1])
	else:
		return "Unknown command"

def handle_connection(client, address):
	while True:
		try:
			request = client.recv(1024).decode('utf-8')
			response = handle_command(request)
			client.sendall(response.encode('utf-8'))
		except:
			print(f"Client: {address} connection close")
			break
	client.close()

def start_server(host_ip='192.168.0.108', port=6677):
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((host_ip, port))
	server_socket.listen()

	print(f"Server started on {host_ip} : {port}")

	while True:
		try:
			client_socket, address = server_socket.accept()
			print(f"Accepted connection from {address[0]} : {address[1]}")
			# Threading 
			client_handler_thread = threading.Thread(target=handle_connection, args=(client_socket,address))
			client_handler_thread.start()
		except:
			break
	server_socket.close()

if __name__ == '__main__' :
	start_server()
