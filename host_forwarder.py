import argparse
import socket
import threading
from scapy.all import *
# import IN

#  This is the file that a real external client will use to send data


parser = argparse.ArgumentParser(description='Server')
# parser.add_argument('--internal_address', type=str, help='Internal mininet address')
# parser.add_argument('--intermediate_address', type=str, help='')
# parser.add_argument('--intermediate_port', type=int, help='')
# parser.add_argument('--destination_address', type=str, help='')
# parser.add_argument('--destination_port', type=int, help='')
# parser.add_argument('--origin_id', type=str)
parser.add_argument('--veth_intf', type=str)
parser.add_argument('--src_ip', type=str)
args = parser.parse_args()

INTF = args.veth_intf

LISTEN_SOCKET, SEND_SOCKET = None, None

# Form the data to transmit
def custom_marshall(message):

    message_to_send = message#':'.join([destination_id, origin_id, message])
    return message_to_send.encode()


def forward(pkt):
    print(pkt.summary())
    
    print("Forwarding to " + str(INTF))
    sendp(pkt, iface=INTF)


# Meant to send to physical interface and out to rpi
def print_pkt(pkt):
    print("OUT!")
    print(pkt.summary())
    # print(pkt.src)
    # flip the src and destination

    # print(pkt[IP])
    src_ip = pkt[IP].src
    dst_ip = pkt[IP].dst
    src_mac = pkt.src
    dst_mac = pkt.dst

    print("Received")
    print(pkt.payload)
    # print(src_mac)

    # Sending from source enp8s0 and dstination of the rpi
    # spoofed_packet = Ether(src="9c:5c:8e:d1:f0:93", dst="dc:a6:32:c1:f1:9f") / IP(src=dst_ip, \
    #             dst=src_ip) \
    #             / UDP(sport=55000, dport=55000) / "reply".encode()
    # spoofed_packet = IP(src=src_ip, \
    #             dst=dst_ip) \
    #             / UDP(sport=55000, dport=55000) / pkt.payload
    # sendp(spoofed_packet, iface="enp8s0")
    send(pkt.payload)
    # sendp(pkt, iface="enp8s0")
    # SEND_SOCKET.send(bytes(spoofed_packet))
    # SEND_SOCKET.sendto(bytes(pkt.payload), (str(dst_ip), 55000))

    # print("Sending to " + src_ip)


# Listens on enp8s0
# MAKE SURE WE DO NOT LISTEN TO OUR OWN SRC MAC
def listen_thread1():


    # Create socket

    print("Start listening on " + str(args.src_ip))
    # Source IP should match this host
    filter='src host ' + args.src_ip + ' and dst port 55000 and not ether src host 9c:5c:8e:d1:f0:93'
    print("Hearing from source...")
    sniff(iface="enp8s0", filter=filter, prn=forward)


# Listen on destination - this sends to physical rpi hosts
#   ONE SIDE NOTE - I am flipping the src/dest packets.  When RPI1 comes back, fix this.
def listen_thread2():
    # Create socket

    print("Start listening...")
    # filter='dst host ' + args.src_ip + ' and dst port 55000'
    # Destination IP should  match this host
    filter='dst host ' + args.src_ip + ' and dst port 55000'
    # filter = ''
    # print("Filtering on " + filter)
    sniff(iface=args.veth_intf, filter=filter, prn=print_pkt)



if __name__ == "__main__":

    # Set up the socket
    # ETH_P_ALL=3
    # LISTEN_SOCKET=socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    # LISTEN_SOCKET.bind((INTF, 0))
    # print("Listening on " + str(INTF))

    # LISTEN_SOCKET.bind(("enp8s0", 0))
    # LISTEN_SOCKET.settimeout(10)


    # SEND_SOCKET=socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    # SEND_SOCKET.bind((INTF, 0))

    SEND_SOCKET=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # SEND_SOCKET.bind((INTF, 0))

    server_listen = threading.Thread(target=listen_thread1)
    server_listen.start()

    server_listen2 = threading.Thread(target=listen_thread2)
    server_listen2.start()