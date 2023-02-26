# host.py
#  This file manages 2 threads:
#  One for receiving and another for transmitting
#   Importantly, it must convert between real and virtual addresses.


import argparse
import socket
import threading
import time

parser = argparse.ArgumentParser(description='Server')
parser.add_argument('--internal_address', type=str, help='Internal mininet address')
parser.add_argument('--internal_port', type=int, help='Port receving data')
parser.add_argument('--external_address', type=str)
parser.add_argument('--external_port', type=int)
# parser.add_argument('--ip_to_sensors', type=str, help='Address to send data to sensors')
# parser.add_argument('--port_to_sensors', type=int, help='Port sending data to sensors')
args = parser.parse_args()

LISTEN_SOCKET, SEND_SOCKET, SEND_ADDR = None, None, None


# I'm going to assume the data will have a 'header' field like
#   data = "10.0.0.1:55000:some_bytes"
def parse_mininet_address(data):
    decoded_str = data.decode().split(":")
    mininet_ip = decoded_str[0]
    mininet_port = int(decoded_str[1])
    remaining_data = ''.join(decoded_str[2:])

    mininet_addr = (mininet_ip, mininet_port)
    return mininet_addr, remaining_data


#  Forward data from current virtual address to real address
def forward_to_addr(data, addr):
    SEND_SOCKET.sendto(data, addr)


# First, set up a listening thread for receiving data
#  Note - this receives two types of data
#    One is from the virtual network, in which case it just directly maps
#     and sends to the corresponding external IP
#    Another is from the real network, in which case it has to 
#       read in the destination (which is an external IP), but has to translate
#       into the mininet IP and send it.
def listen_thread():

    print("Set up listener...")

    while True:
        data, address = LISTEN_SOCKET.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        if len(data):
            
            # If this is from the virtual network
            if address[0][:2] == "10":
                # forward_to_addr(data, SEND_ADDR)
                print("From virtual network")

            # If this is from the real network
            else:
                mininet_addr, data_to_send = parse_mininet_address(data)
                forward_to_addr(data_to_send, mininet_addr)
                print("From Real network")


# Set up another thread for sending data

if __name__ == "__main__":

    print(args.internal_address)
    
    # Set up the socket
    LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    LISTEN_SOCKET.bind(('', args.internal_port))

    # Set up the real node socket
    SEND_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SEND_ADDR = (args.external_address, args.external_port)

    server_listen = threading.Thread(target=listen_thread)
    # server_listen.daemon = True
    server_listen.start()