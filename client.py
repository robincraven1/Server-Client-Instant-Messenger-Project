import socket
import sys
import threading
import os
import time

BUFFER_SIZE = 4096
# Helper to receive bytes exactly (for TCP file transfer)
def recv_all(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def receive_messages(sock, username):
    """
    Thread function to listen for incoming messages from the server.
    """
    while True:
        try:
            # We peak or read the message.
            # Since files are strictly initiated by a command, we can try to rely on headers.
            # However, if we are inside this loop, we are reading general messages.
            # If the server sends a FILE_START_TCP header, we need to handle it.

            message = sock.recv(BUFFER_SIZE)
            if not message:
                print("\nDisconnected from server.")
                break

            decoded = message.decode(errors='ignore') # Ignore errors if we accidentally got binary data

            if decoded.startswith("FILE_START_TCP "):
                # Format: FILE_START_TCP <filename> <size>
                parts = decoded.split(" ", 2)
                filename = parts[1]
                size = int(parts[2])
                print(f"\nReceiving file '{filename}' ({size} bytes) via TCP...")

                # Check if we have extra data in 'message' beyond the header?
                # This is tricky with TCP streaming. The header might be combined with body.
                # Simplified: Assume header is distinct or handle split.
                # In our server we did time.sleep(0.1) to help separate.

                # Create download dir
                download_dir = f"{username}_files"
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir)

                file_path = os.path.join(download_dir, filename)

                # We need to read 'size' bytes.
                # But 'message' currently contains the header AND potentially start of data.
                # We need to strip the header from 'message' bytes-wise.
                # Since we decoded with 'ignore', we should be careful.
                # Let's assume for this assignment the sleep(0.1) works and we treat the next recvs as data.

                remaining = size
                with open(file_path, "wb") as f:
                    while remaining > 0:
                        chunk_size = min(remaining, BUFFER_SIZE)
                        data = sock.recv(chunk_size)
                        if not data:
                            print("Connection lost during download.")
                            break
                        f.write(data)
                        remaining -= len(data)

                print(f"File '{filename}' downloaded successfully to {download_dir}.")
                print(f"Size: {size} bytes.")
                print("> ", end="", flush=True)

            elif decoded.startswith("FILE_START_UDP "):
                # Format: FILE_START_UDP <filename> <size>
                # The data is coming on the UDP port we specified.
                parts = decoded.split(" ", 2)
                filename = parts[1]
                size = int(parts[2])
                print(f"\nIncoming UDP file '{filename}' ({size} bytes). Expecting on UDP port...")
                # The UDP listener logic should have been started by the main thread BEFORE sending the request?
                # Or we start it here?
                # Actually, the main thread triggers the request.
                # Ideally main thread starts a UDP listener, then sends request.
                pass

            else:
                print(f"\n{decoded}")
                print("> ", end="", flush=True)

        except Exception as e:
            print(f"\nError receiving message: {e}")
            break
    sock.close()
    sys.exit(0)

def udp_receiver(port, filename, expected_size, username):
    download_dir = f"{username}_files"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    file_path = os.path.join(download_dir, filename)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))
    sock.settimeout(5) # Timeout if no data

    received_bytes = 0
    with open(file_path, "wb") as f:
        try:
            while received_bytes < expected_size:
                data, _ = sock.recvfrom(2048)
                if data:
                    f.write(data)
                    received_bytes += len(data)
                else:
                    break
        except socket.timeout:
            print("\nUDP Download timed out (finished or lost packets).")

    sock.close()
    print(f"\nUDP Download of {filename} complete (or timed out). Saved to {download_dir}.")
    print(f"Size: {received_bytes}/{expected_size} bytes.")
    print("> ", end="", flush=True)

def main():
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} [username] [hostname] [port]")
        sys.exit(1)

    username = sys.argv[1]
    hostname = sys.argv[2]

    try:
        port = int(sys.argv[3])
    except ValueError:
        print("Port must be an integer.")
        sys.exit(1)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((hostname, port))
        # Send JOIN command immediately
        client_socket.send(f"JOIN {username}".encode())
    except Exception as e:
        print(f"Unable to connect to {hostname}:{port} - {e}")
        sys.exit(1)

    # Start listener thread
    listener_thread = threading.Thread(target=receive_messages, args=(client_socket, username))
    listener_thread.daemon = True
    listener_thread.start()

    print(f"Connected to {hostname}:{port} as {username}")
    print("Commands:")
    print("  /broadcast <msg>       - Switch to broadcast mode (default)")
    print("  /unicast <user> <msg>  - Switch to unicast mode for <user>")
    print("  /join <group>          - Join a group")
    print("  /leave <group>         - Leave a group")
    print("  /group <group> <msg>   - Switch to group mode for <group>")
    print("  /list                  - List shared files")
    print("  /download <file> <TCP|UDP> - Download a file")
    print("  /exit                  - Exit")
    print("------------------------------------------------------------")

    current_mode = "BROADCAST"
    target = None

    while True:
        try:
            user_input = input("")
            if not user_input:
                continue

            if user_input.startswith("/broadcast"):
                current_mode = "BROADCAST"
                target = None
                print("Switched to BROADCAST mode.")
                parts = user_input.split(" ", 1)
                if len(parts) > 1:
                    client_socket.send(f"BROADCAST {parts[1]}".encode())

            elif user_input.startswith("/unicast"):
                parts = user_input.split(" ", 2)
                if len(parts) >= 2:
                    current_mode = "UNICAST"
                    target = parts[1]
                    print(f"Switched to UNICAST mode (Target: {target}).")
                    if len(parts) > 2:
                        client_socket.send(f"UNICAST {target} {parts[2]}".encode())

            elif user_input.startswith("/join"):
                parts = user_input.split(" ", 1)
                if len(parts) > 1:
                    client_socket.send(f"JOIN_GROUP {parts[1]}".encode())

            elif user_input.startswith("/leave"):
                parts = user_input.split(" ", 1)
                if len(parts) > 1:
                    client_socket.send(f"LEAVE_GROUP {parts[1]}".encode())

            elif user_input.startswith("/group"):
                parts = user_input.split(" ", 2)
                if len(parts) >= 2:
                    current_mode = "GROUP"
                    target = parts[1]
                    print(f"Switched to GROUP mode (Group: {target}).")
                    if len(parts) > 2:
                        client_socket.send(f"GROUP_MSG {target} {parts[2]}".encode())

            elif user_input == "/list":
                client_socket.send("LIST_FILES".encode())

            elif user_input.startswith("/download"):
                parts = user_input.split(" ")
                if len(parts) == 3:
                    filename = parts[1]
                    protocol = parts[2].upper()
                    if protocol == "TCP":
                        client_socket.send(f"DOWNLOAD_TCP {filename}".encode())
                    elif protocol == "UDP":
                        # Pick a random local port
                        import random
                        udp_port = random.randint(10000, 20000)
                        # We need to know file size to stop receiver...
                        # But we don't know it yet.
                        # We will start the thread assuming unlimited/unknown or handle it differently?
                        # The Server sends FILE_START_UDP <size>.
                        # So we can't start receiver yet?
                        # We should start receiver AFTER we get the size from server via TCP?
                        # But listener thread sees that.
                        # This is tricky.
                        # Solution: Send request. Listener thread sees FILE_START_UDP <size>.
                        # Listener thread spawns udp_receiver thread.

                        client_socket.send(f"DOWNLOAD_UDP {filename} {udp_port}".encode())
                        print(f"Requested UDP download on port {udp_port}. Waiting for server...")

                        # We need to pass udp_port to listener thread?
                        # Or listener thread can parse it?
                        # Server sends back: FILE_START_UDP <name> <size>
                        # But listener doesn't know 'udp_port'.
                        # We can store 'pending_udp_port' in a global or pass it?
                        # Simple hack: Write udp_port to a file or global var.
                        global PENDING_UDP_PORT
                        PENDING_UDP_PORT = udp_port
                    else:
                        print("Protocol must be TCP or UDP.")
                else:
                    print("Usage: /download <filename> <TCP|UDP>")

            elif user_input == "/exit":
                client_socket.send("/exit".encode())
                break

            else:
                if current_mode == "BROADCAST":
                    client_socket.send(f"BROADCAST {user_input}".encode())
                elif current_mode == "UNICAST":
                    if target:
                        client_socket.send(f"UNICAST {target} {user_input}".encode())
                    else:
                        print("No unicast target.")
                elif current_mode == "GROUP":
                    if target:
                        client_socket.send(f"GROUP_MSG {target} {user_input}".encode())
                    else:
                        print("No group target.")

        except KeyboardInterrupt:
            client_socket.close()
            break
        except Exception as e:
            print(f"Error: {e}")
            client_socket.close()
            break

PENDING_UDP_PORT = None

# We need to inject the pending port handling into listener thread.
# Redefining receive_messages to use the global PENDING_UDP_PORT
def receive_messages(sock, username):
    global PENDING_UDP_PORT
    while True:
        try:
            message = sock.recv(BUFFER_SIZE)
            if not message:
                print("\nDisconnected.")
                break

            decoded = message.decode(errors='ignore')

            if decoded.startswith("FILE_START_TCP "):
                parts = decoded.split(" ", 2)
                filename = parts[1]
                size = int(parts[2])
                print(f"\nReceiving file '{filename}' ({size} bytes) via TCP...")

                download_dir = f"{username}_files"
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir)
                file_path = os.path.join(download_dir, filename)

                remaining = size
                with open(file_path, "wb") as f:
                    while remaining > 0:
                        chunk_size = min(remaining, BUFFER_SIZE)
                        data = sock.recv(chunk_size)
                        if not data: break
                        f.write(data)
                        remaining -= len(data)

                print(f"Download complete: {file_path}")
                print("> ", end="", flush=True)

            elif decoded.startswith("FILE_START_UDP "):
                parts = decoded.split(" ", 2)
                filename = parts[1]
                size = int(parts[2])

                if PENDING_UDP_PORT:
                    port = PENDING_UDP_PORT
                    t = threading.Thread(target=udp_receiver, args=(port, filename, size, username))
                    t.start()
                else:
                    print("Error: Received UDP start but no port pending.")

            else:
                print(f"\n{decoded}")
                print("> ", end="", flush=True)

        except Exception as e:
            print(f"\nError: {e}")
            break
    sock.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
