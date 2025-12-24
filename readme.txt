Instant Messenger - NS2 Coursework
================================

Files Included:
- server.py: The server implementation handling multiple clients, messaging, and file transfers.
- client.py: The client implementation with a threaded listener and command processing.
- readme.txt: This file.

Requirements:
- Python 3.13 (or compatible 3.x)
- Windows OS (as per assignment requirement, though code is cross-platform compatible in principle)

Usage Instructions:

1. Starting the Server:
   Open a terminal and run:
   python server.py <port>

   Example:
   python server.py 12000

   The server will start listening on all interfaces (0.0.0.0) on the specified port.
   It creates a 'SharedFiles' directory automatically. Place files in this directory to share them.

2. Starting a Client:
   Open a separate terminal (or multiple) and run:
   python client.py <username> <hostname> <port>

   Example:
   python client.py Alice 127.0.0.1 12000

3. Messaging Commands:
   The client supports several modes. The prompt will display received messages clearly.

   - Broadcast (Default): Send a message to all other connected clients.
     Usage: Just type your message.
     Or explicitly switch: /broadcast <message>

   - Unicast (Private Message): Send a message to a specific user.
     Usage: /unicast <username> <message>
     This switches your mode to UNICAST. Subsequent messages will go to that user until you switch back.

   - Groups (Multicast):
     Join a group: /join <group_name>
     Leave a group: /leave <group_name>
     Send to group: /group <group_name> <message>
     This switches your mode to GROUP.

   - Exit:
     /exit
     Disconnects cleanly from the server.

4. File Transfer:
   Files must be present in the 'SharedFiles' folder on the server.
   Downloaded files are saved to a folder named '<username>_files' on the client.

   - List Files:
     /list
     Displays all available files in 'SharedFiles' and the total count.

   - Download via TCP:
     /download <filename> TCP
     Example: /download welcome.txt TCP
     Reliable transfer using the existing TCP connection.

   - Download via UDP:
     /download <filename> UDP
     Example: /download video.mp4 UDP
     Transfer using a separate UDP socket. Useful for demonstration of protocol selection.
     Note: Implementation uses a pragmatic sleep mechanism to simulate streaming; large files might have packet loss on unreliable networks.

Implementation Notes:
- The Server uses `select.select` for handling concurrent TCP connections efficiently.
- The Client uses a separate `threading.Thread` to listen for incoming messages while the main thread waits for user input.
- Detailed status messages are printed on the Server console (connections, disconnections, message routing).