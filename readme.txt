===============================================
Instant Client-Server Messenger - Robin Craven
===============================================

Files Included:
- server.py: A server implementation handling multiple clients, with messaging and file transfers
- client.py: A client implementation with a threaded listener and command processing
- SharedFiles: A directory containing files collectively shared by clients

System Requirements:
- Requires Python 3.x
- Windows OS

================================================

Starting the Server:
    Open a terminal and run: <python server.py <port>>
    The server will start listening on all interfaces (0.0.0.0) on the specified port.
    It creates a 'SharedFiles' directory automatically. Place files in this directory.

Starting a Client:
    Open a separate terminal and run: <python client.py <username> <hostname> <port>>
    The client connects to server and displays a welcome message with list of available commands
    Commands for: messaging modes, file transfer, exit.

Messaging Commands:
    1. BROADCAST MODE (Default)
        Explicitly switch to mode with: /broadcast <message>
        Sends a message to all other connected clients

    2. UNICAST MODE (Private Message)
        Explicitly switch to mode with: /unicast <username> <message>
        Sends a message to a specific user

    3. GROUP MODE (Multicast)
        Join/Create a group: /join <group_name>
        Leave a group: /leave <group_name>
        Send to group: /group <group_name> <message>

    4. Exit:
        Disconnect cleanly from the server: /exit

File Transfer:
    1. LIST FILES:
        List the files in 'SharedFiles' and the total count: /list

    2. DOWNLOAD VIA TCP:
        Download via TCP: /download <filename> TCP
        Downloaded files are saved to a folder named '<username>_files'
        Downloads using the same TCP socket as messaging

    3. DOWNLOAD VIA UDP:
        Download via UDP: /download <filename> UDP
        Downloaded files are saved to a folder named '<username>_files'
        Downloads using a different set of sockets than messaging
        Server uses a time.sleep(0.001) pause after sending each chunk of file
        So that buffer overflow (packet loss) does not occur at receiver

        NOTE: UDP transfers are implemented as 'best-effort' without packet recovery.
        On unreliable networks, large files may experience packet loss compared to the reliable TCP mode.

Implementation Notes:
- Server uses `select.select` for handling concurrent TCP connections efficiently
- Client uses a separate `threading.Thread` to listen for incoming messages while the main thread waits for user input
- Detailed status messages are printed on the Server console (connections, disconnections, message routing)

----------------------------------------
REQUIREMENTS CHECKLIST & IMPLEMENTATION DETAILS
----------------------------------------

WHEN CLIENT CONNECTS/DISCONNECTS FROM SERVER:
9.  On the Server: print where connection from (IP+Port)
10. On the Client: display welcome message from server (via sockets)
11. Allow multiple Clients to connect to the same Server
12. Provide input prompt on each client to allow Client to send messages
13. Print "[username] has joined" on all connected Clients when client connect
14. Allow Client to leave the system by implementing a command, or unexpected
15. Print "[username] has left" on all other connected Clients
16. One connected client disconnecting should not cause the server to crash

WHEN CLIENT SENDS A MESSAGE:
17. Client able to send multiple messages
18. Client able to broadcast a message to clients in its group, excl itself
19. Client able to unicast message to individual client when several clients
20. Clients can join or leave a named group with commands.
21. If a group does not exist, the attempt to join will create the group.
22. Clients can send a message to all other clients in the group only.
23. This is to develop multicast where a message can be sent
to multiple (i.e., within the same group) but not all receivers.
24. Client should be able to change between the above messaging modes

WHEN FILE DOWNLOADING:
25. Server has one “SharedFiles” folder
26. Clients able to access folder by with command
27. Uses environment variable SERVER_SHARED_FILES to find this folder
28. Server replies with successful access message and number files in folder
29. This is sent and displayed on client via connection socket (not hardcoded)
30. The list of files in folder is also displayed on Client
31. Client can download any files (text, image, audio, video) from folder
32. Downloaded files should be put in a folder named by the username of Client
33. Client should be able to select protocols (TCP or UDP) for file downloading
34. Protocol is selected on client terminals with a command
35. Display the size (in bytes) for each downloaded file on Client prompt
36. Sent over a network socket (not hardcoded)