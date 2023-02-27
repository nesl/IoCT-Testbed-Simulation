# host.py
#  This file manages 2 threads:
#  One for receiving and another for transmitting
#   Importantly, it must convert between real and virtual addresses.


import argparse
import socket
import threading
import time
import json

parser = argparse.ArgumentParser(description='Server')
parser.add_argument('--device_id', type=str, help='')
args = parser.parse_args()

LISTEN_SOCKET, SEND_SOCKET, HOST_DATA = None, None, None



# I'm going to assume the data will have a 'header' field like
#   data = "host_id:some_bytes"
def parse_mininet_address(data, config_data):
    decoded_str = data.decode().split(":")
    destination_id = decoded_str[0]

    # Get the port of the virtual host id
    mininet_port = config_data[destination_id]["internal_port"]
    mininet_ip = config_data[destination_id]["internal_ip"]

    mininet_addr = ('', mininet_port)
    return mininet_addr, data

#  Forward data to a destination.
#    If the current mininet virtual host matches the destination, send over LAN
#    Otherwise, pass it as it is, to the mininet address.
def forward_to_addr(data, addr, config_data):

    send_addr = addr
    if HOST_DATA["internal_port"] == addr[1]:
        send_addr = (HOST_DATA["external_ip"], HOST_DATA["external_port"])

    SEND_SOCKET.sendto(data, send_addr)
    print("Sending message to " + str(send_addr))


# First, set up a listening thread for receiving data
#  Note - this receives two types of data
#    One is from the virtual network, in which case it just directly maps
#     and sends to the corresponding external IP
#    Another is from the real network, in which case it has to 
#       read in the destination (which is an external IP), but has to translate
#       into the mininet IP and send it.
def listen_thread():

    print("Set up listener...")

    # First, read in our config file
    f = open("config.json")
    config_data = json.load(f)
    f.close()

    while True:
        data, address = LISTEN_SOCKET.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        if len(data):
            mininet_addr, data_to_send = parse_mininet_address(data, config_data)
            forward_to_addr(data_to_send, mininet_addr, config_data)
                


# Set up another thread for sending data

if __name__ == "__main__":

    # Get the current device information
    device_id = args.device_id
    f = open("config.json")
    config_data = json.load(f)
    f.close()
    HOST_DATA = config_data[device_id]
    
    # Set up the socket
    LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    LISTEN_SOCKET.bind(('', HOST_DATA["internal_port"]))



    # Set up the real node socket
    SEND_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server_listen = threading.Thread(target=listen_thread)
    # server_listen.daemon = True
    server_listen.start()