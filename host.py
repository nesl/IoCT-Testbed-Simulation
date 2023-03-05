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

LISTEN_SOCKET, SEND_SOCKET_INTERNAL, HOST_DATA = None, None, None
HOSTNAME = args.device_id


# So there are two ways that a mininet host decides it's desination address.
#  It will get two types of src/destination pairs.
#   - source_ip is the switch: this means that this host is the 'end goal' and must
#       send to the switch back to the real world
#       This requires sending a packet with src=host and dst=switch
#   - source_ip is a host: this means that this host must send data to the 
#       src address.
#       This requires sending a packet with src=switch and dst=host (in the source ip)
def forward_packet(src_ip, config_data, data):
    

    # destination_ip, source_ip = "", src_ip
    # # Does source match destination?
    # if src_ip == config_data["switch"]["internal_ip"]:  # Send to switch
    #     destination_ip = config_data["switch"]["internal_ip"]
    # else:   # Send to a host
    #     destination_ip = src_ip
    #     source_ip = config_data["switch"]["internal_ip"]

    # spoofed_packet = IP(src=source_ip, dst=destination_ip) \
    #     / UDP(sport=55000, dport=55000) / data
    
    # Now, just send a packet back to the switch
    send_addr = ( config_data["switch"]["internal_ip"], 55000)
    print("sending data back to " + str(send_addr))
    SEND_SOCKET_INTERNAL.sendto(data, send_addr)

    # Something to test - it's possible that the controller
    #  is actually managing the delays and it only works between hosts.
    #  So this means that at some point you will need a host to send
    #  a packet with an IP header where both src and dst are hosts.
    #  Of course, you can always add to the data packet for parsing.


# This parses the incoming ethernet frame
def parse_ethernet_frame(data, config_data):

    results = {}

    output = Ether(data)
    protocols = output[0]

    #  Only return results for forwarding if we want this packet.
    if protocols.haslayer(UDP) and protocols.haslayer(IP) and \
        "10.0.1." in str(output[IP].dst) and \
        str(output[IP].src) != config_data[HOSTNAME]["external_ip"]:

        results["src_ip"] = str(output[IP].src)
        results["dst_ip"] = str(output[IP].dst)
        results["data"] = bytes(output[UDP].payload)

    return results

# Get the mapping to an internal mininet address or external address
def get_translated_address(recv_ip, config_data):
    
    translated_address = ""
    for node in config_data.keys():
        if config_data[node]["external_ip"] == recv_ip:
            translated_address = config_data[node]["internal_ip"]
        elif config_data[node]["internal_ip"] == recv_ip:
            translated_address = config_data[node]["external_ip"]
    
    return translated_address


def listen_thread():

    print("Set up listener...")

    # First, read in our config file
    f = open("config.json")
    config_data = json.load(f)
    f.close()

    while True:
        data, src_address = LISTEN_SOCKET.recvfrom(512)

        parsed_results = parse_ethernet_frame(data, config_data)
        if parsed_results:
            print(parsed_results)

            spoofed_packet = None
            # Now we have to alter some behavior.  If the destination ip
            #   matches the current device IP, we conver to global ips.
            if parsed_results["dst_ip"] == config_data[HOSTNAME]["internal_ip"]:
                external_dst_ip = get_translated_address(parsed_results["dst_ip"], config_data)
                spoofed_packet = IP(src=parsed_results["src_ip"], \
                dst=external_dst_ip) \
                / UDP(sport=55000, dport=55000) / parsed_results["data"]
            else:# Otherwise, we forward as normal, changing the src IP to external
                external_src_ip = get_translated_address(parsed_results["src_ip"], config_data)
                spoofed_packet = IP(src=external_src_ip, \
                dst=parsed_results["dst_ip"]) \
                / UDP(sport=55000, dport=55000) / parsed_results["data"]
            
            send(spoofed_packet)

        # print("Recieved addr: " + str(src_address))
        # #  Example address: ('10.0.0.2', 48619)
        # # If we receive something
        # print(data.decode())
        # if len(data):
        #     forward_packet(src_address[0], config_data, data)

        # Note to self - we have an issue:
        #  Using the NAT (see commented line in mininet) will change the source IP address
        #   yet not using NAT seems to prevent communication.
        
        # Alter behavior

        
                


# Set up another thread for sending data

if __name__ == "__main__":

    # Get the current device information
    device_id = args.device_id
    f = open("config.json")
    config_data = json.load(f)
    f.close()
    HOST_DATA = config_data[device_id]
    
    # Set up the socket
    # LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # LISTEN_SOCKET.bind(('', HOST_DATA["external_port"]))

    print("Listening on " + str(HOST_DATA["external_port"]))
    print("on IP: " + HOST_DATA["internal_ip"])

    ETH_P_ALL=3
    LISTEN_SOCKET=socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    LISTEN_SOCKET.bind((args.device_id + "-eth0", 0))

    # Set up the real node socket
    SEND_SOCKET_INTERNAL = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # SEND_SOCKET_INTERNAL = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)

    # if device_id == "host":
    #    SEND_SOCKET_INTERNAL.setsockopt(socket.SOL_SOCKET, 25, 'ts1-eth1'.encode())


    server_listen = threading.Thread(target=listen_thread)
    # server_listen.daemon = True
    server_listen.start()