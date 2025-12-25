import socket
import select
import sys
import os
import time

# Default Settings
HOST = '0.0.0.0'  # Listen on all interfaces
DEFAULT_PORT = 12000
BUFFER_SIZE = 4096

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} [port]")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Port must be an integer.")
        sys.exit(1)

    # initialize server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, port))
        server_socket.listen(5)
        print(f"Server listening on {HOST}:{port}")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

    # Sockets to monitor
    inputs = [server_socket]
    clients = {} # socket -> username
    groups = {}  # group_name -> set(sockets)

    # Helper to broadcast messages (to all clients except sender)
    def broadcast_message(message, sender_socket=None):
        for sock in clients: # Iterate over connected client sockets
            if sock != sender_socket:
                try:
                    sock.send(message.encode())
                except:
                    pass

    # Helper to send to a specific group
    def group_message(group_name, message, sender_socket=None):
        if group_name in groups:
            for sock in groups[group_name]:
                if sock != sender_socket:
                    try:
                        sock.send(message.encode())
                    except:
                        pass

    # Create SharedFiles directory if it doesn't exist
    shared_files_dir = "SharedFiles"
    # Or check environment variable as per spec: "You may consider using the environment variable SERVER_SHARED_FILES"
    # We will use local folder for simplicity as it respects the spec "connect to 127.0.0.1".
    if not os.path.exists(shared_files_dir):
        os.makedirs(shared_files_dir)
        print(f"Created {shared_files_dir} directory.")

    # Create a dummy file for testing
    dummy_file = os.path.join(shared_files_dir, "welcome.txt")
    if not os.path.exists(dummy_file):
        with open(dummy_file, "w") as f:
            f.write("This is a test file served from SharedFiles.")

    print("Server started. Waiting for connections...")

    while True:
        try:
            readable, _, exceptional = select.select(inputs, [], inputs)

            for s in readable:
                if s is server_socket:
                    # New connection
                    client_sock, client_addr = server_socket.accept()
                    print(f"Client connected from {client_addr[0]}:{client_addr[1]}")
                    inputs.append(client_sock)

                    # Send welcome message
                    welcome_msg = "Welcome to the instant messenger!"
                    client_sock.send(welcome_msg.encode())

                else:
                    # Data from an existing client
                    try:
                        data = s.recv(BUFFER_SIZE)
                        if data:
                            msg = data.decode().strip()

                            # Handle JOIN protocol
                            if s not in clients:
                                if msg.startswith("JOIN "):
                                    username = msg.split(" ", 1)[1]
                                    clients[s] = username
                                    print(f"User '{username}' has joined from {s.getpeername()}")
                                    broadcast_message(f"Server: {username} has joined")
                                else:
                                    print(f"Unexpected initial message from {s.getpeername()}: {msg}")
                            else:
                                username = clients[s]

                                # PROTOCOL PARSING
                                if msg.startswith("BROADCAST "):
                                    content = msg.split(" ", 1)[1]
                                    print(f"[Broadcast] {username}: {content}")
                                    broadcast_message(f"[Broadcast] {username}: {content}", sender_socket=s)

                                elif msg.startswith("UNICAST "):
                                    try:
                                        _, target_user, content = msg.split(" ", 2)
                                        target_sock = None
                                        for sock, name in clients.items():
                                            if name == target_user:
                                                target_sock = sock
                                                break

                                        if target_sock:
                                            target_sock.send(f"[PM from {username}]: {content}".encode())
                                            print(f"[Unicast] {username} -> {target_user}: {content}")
                                        else:
                                            s.send(f"Server: User '{target_user}' not found.".encode())
                                    except ValueError:
                                        s.send("Server: Invalid UNICAST format.".encode())

                                elif msg.startswith("GROUP_MSG "):
                                    try:
                                        _, group_name, content = msg.split(" ", 2)
                                        if group_name in groups and s in groups[group_name]:
                                            group_message(group_name, f"[Group {group_name}] {username}: {content}", sender_socket=s)
                                            print(f"[Group {group_name}] {username}: {content}")
                                        else:
                                            s.send(f"Server: You are not a member of group mode: group '{group_name}'.".encode())
                                    except ValueError:
                                        s.send("Server: Invalid GROUP_MSG format.".encode())

                                elif msg.startswith("JOIN_GROUP "):
                                    group_name = msg.split(" ", 1)[1]
                                    if group_name not in groups:
                                        groups[group_name] = set()
                                    groups[group_name].add(s)
                                    s.send(f"Server: You joined group '{group_name}'.".encode())
                                    print(f"{username} joined group {group_name}")

                                elif msg.startswith("LEAVE_GROUP "):
                                    group_name = msg.split(" ", 1)[1]
                                    if group_name in groups and s in groups[group_name]:
                                        groups[group_name].remove(s)
                                        s.send(f"Server: You left group '{group_name}'.".encode())
                                        if not groups[group_name]:
                                            del groups[group_name]
                                    else:
                                        s.send(f"Server: You are not in group '{group_name}'.".encode())

                                elif msg == "LIST_FILES":
                                    files = os.listdir(shared_files_dir)
                                    file_list = "\n".join(files) if files else "No files available."
                                    s.send(f"FILES_LIST {len(files)} files available:\n{file_list}".encode())

                                elif msg.startswith("DOWNLOAD_TCP "):
                                    filename = msg.split(" ", 1)[1]
                                    file_path = os.path.join(shared_files_dir, filename)
                                    if os.path.exists(file_path) and os.path.isfile(file_path):
                                        file_size = os.path.getsize(file_path)
                                        s.send(f"FILE_START_TCP {filename} {file_size}".encode())
                                        # Wait a tiny bit for client to switch mode? No, TCP stream.
                                        # Send file data
                                        time.sleep(0.1) # Brief pause to ensure header is processed separate from body if possible
                                        with open(file_path, "rb") as f:
                                            while True:
                                                bytes_read = f.read(BUFFER_SIZE)
                                                if not bytes_read:
                                                    break
                                                s.send(bytes_read)
                                        print(f"Sent {filename} via TCP to {username}")
                                    else:
                                        s.send(f"Server: File '{filename}' not found.".encode())

                                elif msg.startswith("DOWNLOAD_UDP "):
                                    # Format: DOWNLOAD_UDP <filename> <port>
                                    try:
                                        _, filename, udp_port_str = msg.split(" ", 2)
                                        udp_port = int(udp_port_str)
                                        file_path = os.path.join(shared_files_dir, filename)
                                        if os.path.exists(file_path) and os.path.isfile(file_path):
                                            file_size = os.path.getsize(file_path)
                                            # Send confirmation via TCP
                                            s.send(f"FILE_START_UDP {filename} {file_size}".encode())

                                            # Send via UDP
                                            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                            client_ip = s.getpeername()[0]
                                            print(f"Sending {filename} via UDP to {client_ip}:{udp_port}")

                                            with open(file_path, "rb") as f:
                                                while True:
                                                    chunk = f.read(1024) # Smaller chunk for UDP safety
                                                    if not chunk:
                                                        break
                                                    udp_sock.sendto(chunk, (client_ip, udp_port))
                                                    time.sleep(0.001) # Tiny sleep to prevent packet loss flooding

                                            udp_sock.close()
                                            print(f"Finished UDP send of {filename}")
                                        else:
                                            s.send(f"Server: File '{filename}' not found.".encode())
                                    except ValueError:
                                        s.send("Server: Invalid DOWNLOAD_UDP format.".encode())

                                elif msg == "/exit":
                                    print(f"User '{username}' initiated exit.")
                                    inputs.remove(s)
                                    del clients[s]
                                    for g in groups.values():
                                        if s in g:
                                            g.remove(s)
                                    s.close()
                                    broadcast_message(f"Server: {username} has left")

                                else:
                                    print(f"Unknown command from {username}: {msg}")
                                    s.send("Server: Unknown command or protocol error.".encode())

                        else:
                            # Empty data means disconnect
                            if s in clients:
                                username = clients[s]
                                print(f"Client disconnected: {username}")
                                broadcast_message(f"Server: {username} has left")
                                del clients[s]
                                for g in groups.values():
                                    if s in g:
                                        g.remove(s)
                            else:
                                print(f"Client disconnected: {s.getpeername()}")

                            inputs.remove(s)
                            s.close()
                    except ConnectionResetError:
                        if s in clients:
                            username = clients[s]
                            print(f"Client disconnected abruptly: {username}")
                            broadcast_message(f"Server: {username} has left")
                            del clients[s]
                            for g in groups.values():
                                if s in g:
                                    g.remove(s)
                        else:
                            print("Client disconnected abruptly.")
                        inputs.remove(s)
                        s.close()

            for s in exceptional:
                print(f"Socket exception: {s.getpeername()}")
                inputs.remove(s)
                if s in clients:
                    del clients[s]
                for g in groups.values():
                    if s in g:
                        g.remove(s)
                s.close()

        except KeyboardInterrupt:
            print("\nServer stopping...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            break

    server_socket.close()

if __name__ == "__main__":
    main()
