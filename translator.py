# host.py
#  This file manages 2 threads:
#  One for receiving and another for transmitting
#   Importantly, it must convert between real and virtual addresses.


import argparse
import socket
import threading
import time
import json
from scapy.all import *

parser = argparse.ArgumentParser(description='Server')
parser.add_argument('--device_id', type=str, help='')
args = parser.parse_args()

LISTEN_SOCKET_EXTERNAL, LISTEN_SOCKET_INTERNAL, \
     SEND_SOCKET, HOST_DATA = None, None, None, None
HOSTNAME = args.device_id



# Get the mapping to an internal mininet address or external address
def get_translated_address(recv_ip, config_data):
    
    translated_address = ""
    for node in config_data.keys():
        if config_data[node]["external_ip"] == recv_ip:
            translated_address = config_data[node]["internal_ip"]
        elif config_data[node]["internal_ip"] == recv_ip:
            translated_address = config_data[node]["external_ip"]
    
    return translated_address

#  Forward data to a destination.
#    If the current mininet virtual host matches the destination, send over LAN
#    Otherwise, pass it as it is, to the mininet address.
def forward_to_addr(parsed_results, config_data, send_to_external=False):

    # send_addr = addr
    # send_addr = (parsed_results["src_ip"], 55000)

    translated_src_address = parsed_results["src_ip"]
    translated_dst_address = parsed_results["dst_ip"]
    if not send_to_external:  # If we are sending internally, convert the ips.
        translated_src_address = get_translated_address(parsed_results["src_ip"], config_data)
        translated_dst_address = get_translated_address(parsed_results["dst_ip"], config_data)

    # Now we spoof the ip addresses
    print("Sending data to %s from %s" % (translated_dst_address, translated_src_address))

    send_addr = (translated_dst_address, 55000)

    spoofed_packet = IP(src=translated_src_address, dst=translated_dst_address) \
        / UDP(sport=55000, dport=55000) / parsed_results["data"]
    send(spoofed_packet)

    # SEND_SOCKET_INTERNAL.sendto(parsed_results["data"], send_addr)
    # LISTEN_SOCKET_INTERNAL.send(bytes(spoofed_packet))
    print("Sending message to " + str(send_addr) + "\n\n")


# This parses the incoming ethernet frame
def parse_ethernet_frame(data, config_data):

    results = {}

    output = Ether(data)
    protocols = output[0]


    
    #  Only return results for forwarding if we want this packet.
    #    So we should ignore ethernet frames sent by our own enp8s0 interface
    if output.src != "9c:5c:8e:d1:f0:93" and \
        protocols.haslayer(UDP) and protocols.haslayer(IP) and \
        "10.0.0." in str(output[IP].dst) and \
        str(output[IP].src) != config_data["switch"]["internal_ip"] and \
        str(output[IP].src) != config_data["switch"]["external_ip"] and \
        str(output[IP].src) != "10.0.0.3":

        # print(output.show(dump=True))

        results["src_ip"] = str(output[IP].src)
        results["dst_ip"] = str(output[IP].dst)
        results["data"] = bytes(output[UDP].payload)

    return results


# First, set up a listening thread for receiving data
#  Note - this receives two types of data
#    One is from the virtual network, in which case it just directly maps
#     and sends to the corresponding external IP
#    Another is from the real network, in which case it has to 
#       read in the destination (which is an external IP), but has to translate
#       into the mininet IP and send it.
def listen_thread1():

    print("Set up listener...")

    # First, read in our config file
    f = open("config.json")
    config_data = json.load(f)
    f.close()

    while True:
        data, src_address = LISTEN_SOCKET_EXTERNAL.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        parsed_results = parse_ethernet_frame(data, config_data)
        if parsed_results:
            print("\nRecieved addr: " + str(src_address))
            print(parsed_results)
            forward_to_addr(parsed_results, config_data)

def listen_thread2():

    print("Set up listener 2...")

    # First, read in our config file
    f = open("config.json")
    config_data = json.load(f)
    f.close()

    while True:
        data, src_address = LISTEN_SOCKET_INTERNAL.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        # parsed_results = parse_ethernet_frame(data, config_data)
        parsed_results = parse_ethernet_frame(data, config_data)
        if parsed_results:
            print("\nListener2: Recieved addr: " + str(src_address))
            print(parsed_results)
            forward_to_addr(parsed_results, config_data, send_to_external=True)
            



# Set up another thread for sending data

if __name__ == "__main__":

    # Get the current device information
    device_id = args.device_id
    f = open("config.json")
    config_data = json.load(f)
    f.close()
    HOST_DATA = config_data[device_id]
    
    # Set up the socket
    ETH_P_ALL=3
    LISTEN_SOCKET_EXTERNAL=socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    LISTEN_SOCKET_EXTERNAL.bind(("enp8s0", 0))
    # LISTEN_SOCKET.settimeout(10)

    LISTEN_SOCKET_INTERNAL=socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    LISTEN_SOCKET_INTERNAL.bind(("ts1-eth1", 0))

    # LISTEN_SOCKET_INTERNAL = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # LISTEN_SOCKET_INTERNAL.bind((HOST_DATA["internal_ip"], HOST_DATA["external_port"]))
    # print("Listening on " + str(HOST_DATA["external_port"]))

    # Set up the real node socket
    SEND_SOCKET_INTERNAL = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # SEND_SOCKET_INTERNAL.bind(("ts1-eth1", 0))

    # if device_id == "host":
    # SEND_SOCKET_INTERNAL.setsockopt(socket.SOL_SOCKET, 25, str('ts1-eth1'+'\0').encode())


    server_listen_external = threading.Thread(target=listen_thread1)
    server_listen_external.start()
    server_listen_internal = threading.Thread(target=listen_thread2)
    server_listen_internal.start()

