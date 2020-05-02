import socket
import sys
import subprocess

#Limit total length of control message including file name
LIMIT_LENGTH = 200

# Command line checks
if len(sys.argv) != 2:
    print(f"Usage: python3 {sys.argv[0]} <Port Number>")

# The port on which to listen
# listenPort = 1235
listenPort = int(sys.argv[1])

# Create a server socket
serverSideSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
serverSideSock.bind(('', listenPort))

# Start listening on the socket (server side)
serverSideSock.listen(1)


# ************************************************
# Receives the specified number of bytes
# from the specified socket
# @param sock - the socket from which to receive
# @param numBytes - the number of bytes to receive
# @return - the bytes object received
# *************************************************
def recvAll(sock, numBytes):
    # The buffer
    recvBuff = "".encode()  #convert to 'bytes' object

    # The temporary buffer
    tmpBuff = ""

    # Keep receiving until completing
    while len(recvBuff) < numBytes:

        # Attempt to receive bytes
        tmpBuff = sock.recv(numBytes)

        # The other side has closed the socket
        if not tmpBuff:
            break

        # Add the received bytes to the buffer
        recvBuff += tmpBuff     #tmpBuff: is  a 'bytes' object (already tested)

    return recvBuff


def sendAll(sock, anyData):
    # The number of bytes sent
    numSent = 0

    # Send the data!
    while len(anyData) > numSent:
        numSent += sock.send(anyData[numSent:])


# Accept connections forever
while True:
    print("Waiting for connections...")

    # Accept connections
    clientControlSock, addr = serverSideSock.accept()

    print("Accepted connection from client: ", addr,"\n")
    clientSideSockIP = addr[0]

    while True:
        # Get the control message
        controlMessage = recvAll(clientControlSock, LIMIT_LENGTH)
        testString = controlMessage.strip()
        if testString == b'quit':
            print("Receive 'quit' control message from client - SUCCESS!\n")
            break;
        elif testString[5:8] == b'get':
            nameFileGet = testString[9:]
            clientSideSockPort = int(testString[0:5])

            # Create a TCP socket to client
            serverDataSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("Try to connect to client socket: ", clientSideSockIP, " Port: ", clientSideSockPort, "\n")
            # Connect to the client
            serverDataSock.connect((clientSideSockIP, clientSideSockPort))

            try:
                # Open the file
                fileObj = open(nameFileGet, "rb")
                # The file data
                fileData = fileObj.read()
                dataSize = len(fileData)

                # Initialize number of bytes sent
                bytesSent = 0                
                sendAll(clientControlSock,"FILE FOUND".encode())
                # Keep sending until all is sent
                while bytesSent < dataSize:
                    # Read 65536 bytes of data
                    if bytesSent + 65536 < dataSize:
                        fileDataChunk = fileData[bytesSent:bytesSent+65536]
                    else:
                        fileDataChunk = fileData[bytesSent:]
                    bytesSent += 65536

                    # Get the size of the data read
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

                # The file has been read. We are done
                # Close the file
                fileObj.close()                
                controlMessage = clientControlSock.recv(10) # assume that file is not larger than 9.9GB                
                bytesTransfered = int(controlMessage.decode())
            
                if dataSize == bytesTransfered:
                    print("File '", nameFileGet.decode().strip(), "' is sent to client! - SUCCESS!\n")
                else:
                    print("File '", nameFileGet.decode().strip(), "' cannot be completely sent to client! - FAILURE!\n")                                    
            except FileNotFoundError:
                print("File '", nameFileGet.decode().strip(), "' not found! - FAILURE\n")
                sendAll(clientControlSock,"FILE NOT FOUND".encode())   #find not found from server
            serverDataSock.close()
        elif testString[5:8] == b'put':            
            nameFileGet = testString[9:]
            clientSideSockPort = int(testString[0:5])

            # Create a TCP socket to client
            serverDataSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("Try to connect to client socket: ", clientSideSockIP, " Port: ", clientSideSockPort, "\n")
            # Connect to the client
            serverDataSock.connect((clientSideSockIP, clientSideSockPort))            
            controlMessage = clientControlSock.recv(14) #FILE NOT FOUND | FIND FOUND                        
            testString = controlMessage.strip()
            if testString == b'FILE NOT FOUND':
                print("File not found! - FAILURE\n") 
                continue
            # number of bytes received
            bytesReceived = 0
            while True:
                # The buffer to all data received from the
                # the client.
                chunkData = ""
                # The buffer containing the chunk size
                chunkSizeBuff = ""
                # Receive the first 10 bytes indicating the
                # size of the chunk
                chunkSizeBuff = recvAll(serverDataSock, 10)

                # Get the chunk size
                chunkSize = int(chunkSizeBuff)
                bytesReceived += chunkSize

                if chunkSize == 0:
                    print("File does not exist from client!\n")
                    break

                # Get the chunk data
                chunkData = recvAll(serverDataSock, chunkSize)

                # Open the file and write the data to it >> save the received buffer
                if bytesReceived <= 65536:          # 1st chunk
                    file = open(nameFileGet, 'wb') # create file and write
                else:
                    file = open(nameFileGet, 'ab') # append
                file.write(chunkData)

                # Close the file
                file.close()

                # check if it is last chunk
                if chunkSize < 65536:
                    # print("File '", nameFileGet.decode().strip(), "' is received from client! - SUCCESS!\n")
                    break;              
            serverDataSock.close()            
            sendAll(clientControlSock,str(bytesReceived).encode())
             # check if file is received successfully            
            controlMessage = clientControlSock.recv(10) # assume that file is not larger than 9.9GB            
            testInt = int(controlMessage.decode())
            if testInt == bytesReceived:
                print("File '", nameFileGet.decode().strip(), "' is received from client! - SUCCESS!\n")
            else:
                print("File '", nameFileGet.decode().strip(), "' cannot be completely received from client! - FAILURE!\n")
            
            
        elif testString[5:7] == b'ls':
            # nameFileGet = testString[9:]
            clientSideSockPort = int(testString[0:5])

            # Create a TCP socket to client
            serverDataSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("Try to connect to client socket: ", clientSideSockIP, " Port: ", clientSideSockPort, "\n")
            # Connect to the client
            serverDataSock.connect((clientSideSockIP, clientSideSockPort))         
            fileData = subprocess.check_output(["ls -l"], shell=True)
            dataSize = len(fileData)
            # Initialize number of bytes sent
            bytesSent = 0

            # Run ls command, get output, and sent it
            while bytesSent < dataSize:
                # Read 65536 bytes of data
                if bytesSent + 65536 < dataSize:
                    fileDataChunk = fileData[bytesSent:bytesSent+65536]
                else:
                    fileDataChunk = fileData[bytesSent:]
                bytesSent += 65536

                # Get the size of the data read
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

            # check if client received data completely
            sendAll(clientControlSock,str(dataSize).encode())
            controlMessage = recvAll(clientControlSock, 7)
            testString = controlMessage.strip()
            if testString == b'SUCCESS':
                print("ls command sent data completely! - SUCCESS!\n")
            else:
                print("ls command didn'n send data completely! - FAILURE!\n")

            serverDataSock.close()
        else:
            break

    # Close our control sock
    clientControlSock.close()
    print("Closed connection from client: ", addr, "\n")

