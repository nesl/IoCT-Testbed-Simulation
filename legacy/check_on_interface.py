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
parser.add_argument('--intf', type=str, help='')
args = parser.parse_args()


def print_pkt(pkt):
    print(pkt.summary())


def listen_thread():
    print("Set up listener...")

    # Destination IP should  match this host
    # filter='dst host ' + args.src_ip + ' and dst port 55000'
    # filter = ''
    filter='dst port 55000'
    # print("Filtering on " + filter)
    sniff(iface=args.intf, filter=filter, prn=print_pkt)
        
        
                


# Set up another thread for sending data

if __name__ == "__main__":


    server_listen = threading.Thread(target=listen_thread)
    server_listen.start()