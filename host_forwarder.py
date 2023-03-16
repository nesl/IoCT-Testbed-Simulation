import argparse
import socket
import threading
from scapy.all import *
# from getmac import get_mac_address
# import IN

#  This is the file that a real external client will use to send data
import psutil


def get_mac_address(intf_name):
    mac_address = ""
    for interface, snics in psutil.net_if_addrs().items():
        if intf_name == interface:
            # Get the mac address
            for snic in snics:
                if snic.family == socket.AF_PACKET:
                    mac_address = snic.address
                    break
    return mac_address

#  This gets a packet on enp8s0 and forwards it to the veth interface
def forward_internal(pkt):
    
    print("Forwarding to " + str(args.veth_intf))
    print(pkt.summary())
    sendp(pkt, iface=args.veth_intf)


# Meant to send to physical interface and out to rpi
def forward_external(pkt):
    print("Sending data to external host:")
    print(pkt.summary())

    # Sending from source enp8s0 and dstination of the rpi
    # spoofed_packet = Ether(src="9c:5c:8e:d1:f0:93", dst="dc:a6:32:c1:f1:9f") / IP(src=dst_ip, \
    #             dst=src_ip) \
    #             / UDP(sport=55000, dport=55000) / "reply".encode()

    send(pkt.payload)


# Listens on enp8s0
# MAKE SURE WE DO NOT LISTEN TO OUR OWN SRC MAC
def forward_to_mininet(host_intf, src_ip):

    # Create socket

    print("Start listening on " + str(src_ip))
    # Source IP should match this host

    mac_addr = get_mac_address(host_intf)
    filter='src host ' + src_ip + ' and not ether src host ' + mac_addr + \
    ' and not src port 22'
    print("Hearing from source...")
    sniff(iface=host_intf, filter=filter, prn=forward_internal)


# Listen on destination - this sends to physical or virtual hosts
def forward_to_external_host(veth_intf, src_ip):
    # Create socket

    print("Start listening...")
    # filter='dst host ' + args.src_ip + ' and dst port 55000'
    # Destination IP should  match this host
    filter='dst host ' + src_ip
    sniff(iface=veth_intf, filter=filter, prn=forward_external)



if __name__ == "__main__":

    # Parse the arguments
    parser = argparse.ArgumentParser(description='Server')
    parser.add_argument('--veth_intf', type=str)
    parser.add_argument('--host_intf', type=str)
    parser.add_argument('--src_ip', type=str)
    args = parser.parse_args()

    server_listen = threading.Thread(target=forward_to_mininet, args=(args.host_intf,args.src_ip))
    server_listen.start()

    server_listen2 = threading.Thread(target=forward_to_external_host, args=(args.veth_intf,args.src_ip))
    server_listen2.start()