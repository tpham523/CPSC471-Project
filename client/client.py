import socket
import os
import sys


#Limit total length of control message including port (if have), command, and file name
LIMIT_LENGTH = 200

# Command line checks
if len(sys.argv) != 3:
    print(f"Usage: python3 {sys.argv[0]} <Server Machine> <Server Port>")

# Server address
serverName = sys.argv[1]
serverAddr = socket.gethostbyname(serverName)

# Server port
serverPort = int(sys.argv[2])

# Create a TCP socket
serverControlSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server
serverControlSock.connect((serverAddr, serverPort))


# ************************************************
# Sends all data to the the specified socket
# @param sock - the socket from which to receive
# @param anyData - it can be a control message or
#  data message
# *************************************************
def sendAll(sock, anyData):
    # The number of bytes sent
    numSent = 0

    # Send the data!
    while len(anyData) > numSent:
        numSent += sock.send(anyData[numSent:])


def transformControlMessage(anyControlMesasge):
    # Append SPACE's to the size string
    # until the size is LIMIT_LENGTH bytes
    while len(anyControlMesasge) < LIMIT_LENGTH:
        anyControlMesasge = anyControlMesasge + " "
    return anyControlMesasge.encode()


# ************************************************
# Receives the specified number of bytes
# from the specified socket
# @param sock - the socket from which to receive
# @param numBytes - the number of bytes received
# @return - the bytes object received
# *************************************************
def recvAll(sock, numBytes):
    # The buffer
    recvBuff = "".encode()  #convert to 'bytes' object

    # The temporary buffer
    tmpBuff = ""

    # Keep receiving till all is received
    while len(recvBuff) < numBytes:

        # Attempt to receive bytes
        tmpBuff = sock.recv(numBytes)

        # The other side has closed the socket
        if not tmpBuff:
            break

        # Add the received bytes to the buffer
        recvBuff += tmpBuff     #tmpBuff: is  a 'bytes' object (already tested)

    return recvBuff


command = ""
while True:
    #print("ftp> ")
    command = input("ftp> ")
    if command == "quit":
        #serverControlSock.send(command.encode()) # send control message to server
        sendAll(serverControlSock,transformControlMessage(command))
        break

    if command[0:3] == "get":
        # Create a socket
        clientSideSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to port 0
        clientSideSock.bind(('', 0))
        # Retrieve the ephemeral port number
        clientSideSockPort = clientSideSock.getsockname()[1]
        # Start listening on the socket (client side)
        clientSideSock.listen(1)

        # make sure port length is 5
        if clientSideSockPort < 100:
            command += "000" + str(clientSideSockPort) + command
        elif clientSideSockPort < 1000:
            command += "00" + str(clientSideSockPort) + command
        elif clientSideSockPort < 10000:
            command = "0" + str(clientSideSockPort) + command
        else:
            command = str(clientSideSockPort) + command
        sendAll(serverControlSock, transformControlMessage(command))

        # Accept connections
        serverDataSock, addr = clientSideSock.accept()
        # Get filename
        saveFileName = command[9:].strip()

        controlMessage = serverControlSock.recv(20) #FILE NOT FOUND | FIND FOUND 
        testString = controlMessage.strip()
        if testString == b'FILE NOT FOUND':
            print("File not found!\n") 
            continue

        # number of bytes received
        bytesReceived = 0
        while True:
            # The buffer of chunk data received from the
            # the server.
            chunkData = ""
            # The buffer containing the chunk size
            chunkSizeBuff = ""
            # Receive the first 10 bytes indicating the
            # size of the chunk
            chunkSizeBuff = recvAll(serverDataSock, 10)

            # Get the chunk size
            chunkSize = int(chunkSizeBuff)
            bytesReceived += chunkSize

            # if chunkSize == 0:
            #     bytesReceived = 0
            #     print("File not found!\n")                
            #     break

            # Get the chunk data
            chunkData = recvAll(serverDataSock, chunkSize)

            # Open the file and write the data to it >> save the received buffer
            if bytesReceived <= 65536:          # 1st chunk, in case file size is too small
                file = open(saveFileName, 'wb') # create file and write
            else:
                file = open(saveFileName, 'ab') # append
            file.write(chunkData)

            # Close the file
            file.close()

            # check if file is sent
            if chunkSize < 65536:
                break;
        clientSideSock.close()        
        sendAll(serverControlSock,str(bytesReceived).encode())        
        print("Filename is ", saveFileName)
        print("Number of bytes transferred are ", bytesReceived, "bytes\n")
                
    elif command[0:3] == "put":
        nameFileGet = command[4:]
        # Create a socket
        clientSideSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to port 0
        clientSideSock.bind(('', 0))
        # Retrieve the ephemeral port number
        clientSideSockPort = clientSideSock.getsockname()[1]
        # Start listening on the socket (client side)
        clientSideSock.listen(1)

        # make sure port length is 5
        if clientSideSockPort < 100:
            command += "000" + str(clientSideSockPort) + command
        elif clientSideSockPort < 1000:
            command += "00" + str(clientSideSockPort) + command
        elif clientSideSockPort < 10000:
            command = "0" + str(clientSideSockPort) + command
        else:
            command = str(clientSideSockPort) + command        
        sendAll(serverControlSock, transformControlMessage(command))        
        # Accept connections
        serverDataSock, addr = clientSideSock.accept()
        
        try:
            # Open the file            
            fileObj = open(nameFileGet, "rb")            
            # The file data
            fileData = fileObj.read()            
            dataSize = len(fileData)
            # Initialize number of bytes sent
            bytesSent = 0                    
            sendAll(serverControlSock,"FILE FOUND    ".encode())            
            # Keep sending until all is sent
            while bytesSent < dataSize:
                # Read 65536 bytes of data
                if bytesSent + 65536 < dataSize:
                    fileDataChunk = fileData[bytesSent:bytesSent+65536]
                else:
                    fileDataChunk = fileData[bytesSent:]
                bytesSent += 65536

                # Get the size of the data
                # and convert it to string
                dataSizeChunk = str(len(fileDataChunk))

                # Prepend 0's to the size string
                # until the size is 10 bytes << need for last chunk
                while len(dataSizeChunk) < 10:
                    dataSizeChunk = "0" + dataSizeChunk

                # Prepend the size of the data to the
                # file data.
                fileDataChunk = dataSizeChunk.encode() + fileDataChunk
                
                sendAll(serverDataSock, fileDataChunk)

            # Close the file
            fileObj.close()
            # Get filename
            saveFileName = command[9:].strip()            
            controlMessage = serverControlSock.recv(10) # assume that file is not larger than 9.9GB            
            bytesTransfered = int(controlMessage.decode())
            print("Filename is ", saveFileName)
            print("Number of bytes transferred are ", bytesTransfered, "bytes\n")
            sendAll(serverControlSock,str(dataSize).encode())
            
        except FileNotFoundError:
            print("File '", nameFileGet, "' not found!")                
            sendAll(serverControlSock,"FILE NOT FOUND".encode())   #find not found from client            
        clientSideSock.close()
    elif command[0:2] == "ls":
        # Create a socket
        clientSideSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to port 0
        clientSideSock.bind(('', 0))
        # Retrieve the ephemeral port number
        clientSideSockPort = clientSideSock.getsockname()[1]
        # Start listening on the socket (client side)
        clientSideSock.listen(1)

        # make sure port length is 5
        if clientSideSockPort < 100:
            command += "000" + str(clientSideSockPort) + command
        elif clientSideSockPort < 1000:
            command += "00" + str(clientSideSockPort) + command
        elif clientSideSockPort < 10000:
            command = "0" + str(clientSideSockPort) + command
        else:
            command = str(clientSideSockPort) + command
        sendAll(serverControlSock, transformControlMessage(command))

        # Accept connections
        serverDataSock, addr = clientSideSock.accept()
        bytesReceived = 0
        while True:
            # The buffer of chunk data received from the
            # the server.
            chunkData = ""
            # The buffer containing the chunk size
            chunkSizeBuff = ""
            # Receive the first 10 bytes indicating the
            # size of the chunk
            chunkSizeBuff = recvAll(serverDataSock, 10)

            # Get the chunk size
            chunkSize = int(chunkSizeBuff)
            bytesReceived += chunkSize

            if chunkSize == 0:  #no file in server
                break

            # Get the chunk data
            chunkData = recvAll(serverDataSock, chunkSize)

            print(chunkData.decode())

            # check if transfering progress is completed
            if chunkSize < 65536:
                break;
        clientSideSock.close()
        # check to send success signal to server
        controlMessage = serverControlSock.recv(10) # assume that file is not larger than 9.9GB
        testInt = int(controlMessage.decode())
        if testInt == bytesReceived:
            sendAll(serverControlSock,"SUCCESS".encode())
        else:
            sendAll(serverControlSock,"FAILURE".encode())
    else:
        print("We only support 'get, put, ls, quit' commands")
# Close the socket
serverControlSock.close()
