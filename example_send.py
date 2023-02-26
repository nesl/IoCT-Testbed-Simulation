import argparse
import socket

parser = argparse.ArgumentParser(description='Server')
# parser.add_argument('--internal_address', type=str, help='Internal mininet address')
parser.add_argument('--destination_address', type=str, help='')
parser.add_argument('--destination_port', type=int, help='')
args = parser.parse_args()



# Create socket
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# addr = (args.destination_address, args.destination_port)
print("Sent data!")
# clientSocket.sendto("hello".encode('utf-8'), addr)


# If this is from a physical node, it can be something like
clientSocket.sendto("10.0.0.2:55001:hello".encode('utf-8'), ('192.168.1.48', 55000))