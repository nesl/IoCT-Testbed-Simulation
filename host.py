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
HOSTNAME = args.device_id


# I'm going to assume the data will have a 'header' field like
#   data = "host_id:some_bytes"
def parse_mininet_address(data, config_data):
    decoded_str = data.decode().split(":")
    destination_id = decoded_str[0]
    source_id = decoded_str[1]

    print(HOSTNAME)
    print(source_id)
    # Get the port of the virtual host id
    mininet_port = config_data[destination_id]["external_port"]
    mininet_ip = config_data[destination_id]["internal_ip"]

    # If this host is named 'switch', instead we send data to the src
    if HOSTNAME == "switch":
        mininet_port = config_data[source_id]["external_port"]
        mininet_ip = config_data[source_id]["internal_ip"]

    # Otherwise, if the current host's IP matches the destination,
    #  Then we send it back to the switch.
    elif mininet_ip == HOST_DATA["internal_ip"]:
        mininet_ip = config_data["switch"]["internal_ip"]
        mininet_port = config_data["switch"]["external_port"]

    mininet_addr = (mininet_ip, mininet_port)
    return mininet_addr, data, destination_id

#  Forward data to a destination.
#    If the current mininet virtual host matches the destination, send over LAN
#    Otherwise, pass it as it is, to the mininet address.
def forward_to_addr(src_address, data, addr, config_data, destination_id):

    send_addr = addr

    # If the source address comes from a virtual address, then instead
    #  Send it to the corresponding PI (external IP)
    if HOSTNAME == "switch" and src_address[0] == config_data[destination_id]["internal_ip"]:
        send_addr = (config_data[destination_id]["external_ip"], config_data[destination_id]["external_port"])

    SEND_SOCKET_INTERNAL.sendto(data, send_addr)
    print("Sending message to " + str(send_addr) + "\n\n")


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
        data, src_address = LISTEN_SOCKET.recvfrom(512)
        print("Recieved addr: " + str(src_address))
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        print(data.decode())
        if len(data):
            mininet_addr, data_to_send, destination_id = parse_mininet_address(data, config_data)
            forward_to_addr(src_address, data_to_send, mininet_addr, config_data, destination_id)
                


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
    LISTEN_SOCKET.bind(('', HOST_DATA["external_port"]))

    print("Listening on " + str(HOST_DATA["external_port"]))

    # Set up the real node socket
    SEND_SOCKET_INTERNAL = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # if device_id == "host":
    #    SEND_SOCKET_INTERNAL.setsockopt(socket.SOL_SOCKET, 25, 'ts1-eth1'.encode())


    server_listen = threading.Thread(target=listen_thread)
    # server_listen.daemon = True
    server_listen.start()