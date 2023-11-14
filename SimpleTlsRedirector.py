#!/usr/bin/env python

import socket
import threading
import select
import sys
import ssl

terminateAll = False
CLIENT_RX_BANNER = b'\n###---------->||---------->###\n'
SERVER_RX_BANNER = b'\n###<----------||<----------###\n'

class ClientThread(threading.Thread):
	def __init__(self, clientSocket, targetHost, targetPort, cert, outFile, count):
		threading.Thread.__init__(self)
		self.__clientSocket = clientSocket
		self.__targetHost = targetHost
		self.__targetPort = targetPort
		self.__cert = cert
		self.__outFD = 0
		if not outFile == '':
			self.__outFD = open(outFile + '_%d' % (count), "wb")
			
	def run(self):
		print("Client Thread started")
		
		self.__clientSocket.setblocking(0)

		targetHostSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		targetHostSocket = context.wrap_socket(targetHostSocket, ca_certs=self.__cert)
		targetHostSocket.connect((self.__targetHost, self.__targetPort))
		targetHostSocket.setblocking(0)



		clientData = b""
		targetHostData = b""
		terminate = False
		while not terminate and not terminateAll:
			inputs = [self.__clientSocket, targetHostSocket]
			outputs = []
			
			if len(clientData) > 0:
				outputs.append(self.__clientSocket)
				
			if len(targetHostData) > 0:
				outputs.append(targetHostSocket)
			
			try:
				inputsReady, outputsReady, errorsReady = select.select(inputs, outputs, [], 1.0)
			except Exception as e:
				print(e)
				break
				
			for inp in inputsReady:
				if inp == self.__clientSocket:
					data = b''
					try:
						data = self.__clientSocket.recv(4096)
					except Exception as e:
						print(e)
					
					if data != None:
						if len(data) > 0:
							if not self.__outFD == 0:
								self.__outFD.write(CLIENT_RX_BANNER)
								self.__outFD.write(data)
							targetHostData += data
						else:
							terminate = True
				elif inp == targetHostSocket:
					data = b''
					try:
						data = targetHostSocket.recv(4096)
					except Exception as e:
						print(e)
						
					if data != None:
						if len(data) > 0:
							if not self.__outFD == 0:
								self.__outFD.write(SERVER_RX_BANNER)
								self.__outFD.write(data)
							clientData += data
						else:
							terminate = True
						
			for out in outputsReady:
				if out == self.__clientSocket and len(clientData) > 0:
					bytesWritten = self.__clientSocket.send(clientData)
					if bytesWritten > 0:
						clientData = clientData[bytesWritten:]
				elif out == targetHostSocket and len(targetHostData) > 0:
					bytesWritten = targetHostSocket.send(targetHostData)
					if bytesWritten > 0:
						targetHostData = targetHostData[bytesWritten:]

		self.__clientSocket.shutdown(socket.SHUT_RDWR)
		self.__clientSocket.close()
		targetHostSocket.close()
		if not self.__outFD == 0:
			self.__outFD.close()
		print("ClienThread terminating")

if __name__ == '__main__':
	if len(sys.argv) != 8 and len(sys.argv) != 9:
		print('Usage:\n\tpython SimpleTlsRedirector <host> <port> <server key path> <server cert path> <remote host> <remote port> <client cert path>')
		print('Example:\n\tpython SimpleTlsRedirector localhost 8080 server_key.pem server_cert.pem www.google.com 80 client_cert.pem')
		sys.exit(0)		
	
	localHost = sys.argv[1]
	localPort = int(sys.argv[2])
	skey = sys.argv[3]
	scert = sys.argv[4]
	targetHost = sys.argv[5]
	targetPort = int(sys.argv[6])
	tcert = sys.argv[7]
	outFile = ''
	if len(sys.argv) == 9:
		outFile = sys.argv[8]

	context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
	context.load_cert_chain(certfile=scert, keyfile=skey)		
	serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	serverSocket.bind((localHost, localPort))
	serverSocket.listen(5)

	print("Waiting for client...")
	connectCount = 0
	while True:
		try:
			clientSocket, address = serverSocket.accept()
			connstream = context.wrap_socket(clientSocket, server_side=True)
		except KeyboardInterrupt:
			print("\nTerminating...")
			terminateAll = True
			break

		connectCount += 1
		ClientThread(connstream, targetHost, targetPort, tcert, outFile, connectCount).start()
		
	serverSocket.close()
