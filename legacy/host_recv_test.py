import argparse
import socket
import threading
from scapy.all import *
# import IN
import fcntl
import struct
import netifaces as ni
#  This is the file that a real external client will use to send data


parser = argparse.ArgumentParser(description='Server')
# parser.add_argument('--internal_address', type=str, help='Internal mininet address')
# parser.add_argument('--intermediate_address', type=str, help='')
# parser.add_argument('--intermediate_port', type=int, help='')
# parser.add_argument('--destination_address', type=str, help='')
# parser.add_argument('--destination_port', type=int, help='')
# parser.add_argument('--origin_id', type=str)
parser.add_argument('--veth_intf', type=str)
parser.add_argument('--mininet_intf', type=str)
parser.add_argument('--internal_ip', type=str)
args = parser.parse_args()

INTF = args.veth_intf

LISTEN_SOCKET, SEND_SOCKET = None, None

# Form the data to transmit
def custom_marshall(message):

    message_to_send = message#':'.join([destination_id, origin_id, message])
    return message_to_send.encode()


def get_ip(interface):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    packed_iface = struct.pack('256s', interface.encode('utf_8'))
    packed_addr = fcntl.ioctl(sock.fileno(), 0x8915, packed_iface)[20:24]
    return socket.inet_ntoa(packed_addr)

# This is called from veth.
def print_pkt(pkt):
    print(pkt.summary())
    destination_ip = pkt[IP].dst
    print(destination_ip)
    print("EGEGEGEGGE")
    # sendp(pkt, iface=args.mininet_intf)
    # SEND_SOCKET.sendto("hi".encode(), (str(destination_ip), 55000))
    sendp(pkt, iface=args.mininet_intf)

# This is called from the rpi-eth0 interface
def send_to_host(pkt):
    sendp(pkt, iface=args.veth_intf)

# This listens on the veth interface and sends to rpi-eth0
#  It makes sure not to read in packets which are destined for this IP
#  so it does not read its own sends.
def listen_thread():
    print("Start listening...")
    filter='dst port 55000 and not dst host ' + args.internal_ip
    # filter=''
    print("Listening on " + args.veth_intf)
    sniff(iface=args.veth_intf, filter=filter, prn=print_pkt)


# This listens on the rpi-eth0 interface and sends to veth
def listen_thread2():

    # print("Set up listener...")
    # clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # clientSocket.bind((INTF, 0))
    # clientSocket.bind(("macvlan1",0))

    print("Listening for dst: %s" % (args.internal_ip))
    filter='dst host ' + args.internal_ip + ' and dst port 55000'
    sniff(iface=args.mininet_intf, filter=filter, prn=send_to_host)

    # # # Create send socket
    # forwarder_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # # socket_ip = ni.ifaddresses(args.veth_intf)[ni.AF_INET][0]['addr']
    # socket_ip = get_ip(args.veth_intf)
    # forwarder_socket.bind((socket_ip, 0))

    # # forwarder_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    # # forwarder_socket.bind((args.veth_intf, 0))

    # print("Start listening...")

    # while True:
    #     data, address = LISTEN_SOCKET.recvfrom(512)
    #     #  Example address: ('10.0.0.2', 48619)
    #     # If we receive something
    #     if len(data):
    #         #Send back to the host forwarder
    #         print("HIHIHIHIHI")
    #         print("Forwarding to " + args.internal_ip)

    #         forwarder_socket.sendto("hi".encode(), ("10.0.0.10", 55000))


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


    SEND_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SEND_SOCKET.bind((args.internal_ip, 0))

    # This listens to the 
    LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    LISTEN_SOCKET.bind((args.internal_ip, 55000))


    server_listen = threading.Thread(target=listen_thread)
    server_listen.start()

    server_listen2 = threading.Thread(target=listen_thread2)
    server_listen2.start()