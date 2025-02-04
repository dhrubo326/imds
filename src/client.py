import socket
import threading

def handle_write(client):
	while True:
		try:
			command = input("get/set/del : ")
			client.sendall(command.encode('utf-8'))
		except:
			break
	client.close()

def handle_read(client):
	while True:
		try:
			response = client.recv(1024).decode('utf-8')
			print(f"Server: {response}")
		except:
			break;
	client.close()

def start_server(host_ip='192.168.0.108', port=6677):
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client_socket.connect((host_ip, port))
	print(f"Client is connect with server on {host_ip} : {port}")

	write_thread = threading.Thread(target=handle_write, args=(client_socket,))
	write_thread.start()
	read_thread = threading.Thread(target=handle_read, args=(client_socket,))
	read_thread.start()

	

if __name__ == '__main__' :
	start_server()
