import argparse
import socket
import threading
import time
from scapy.all import *

#  This is the file that a real external client will use to send data


parser = argparse.ArgumentParser(description='Server')
# parser.add_argument('--internal_address', type=str, help='Internal mininet address')
parser.add_argument('--destination_address', type=str, help='')
# parser.add_argument('--intermediate_port', type=int, help='')
# parser.add_argument('--destination_id', type=str, help='')
# parser.add_argument('--origin_id', type=str)
parser.add_argument('--message', type=str, default="hello from rpi!")
args = parser.parse_args()



LISTEN_SOCKET = None
SEND_TIMESTAMP = 0

def listen_thread():

    print("Set up listener...hi")

    while True:
        data, address = LISTEN_SOCKET.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        if len(data):
            message = data.decode()
            print(message)

            if "reply" in message:
                print("Time difference: %f seconds" % ((time.time() - SEND_TIMESTAMP)/2))
    

# Form the data to transmit
def custom_marshall(message):

    message_to_send = message #':'.join([destination_id, origin_id, message])
    return message_to_send.encode()

if __name__ == '__main__':


    # Here's what we need:
    #  Packet sniffer with BPF on enp8s0, and routes directly to 
    #  the particular veth interface.  In this case, veth_host1.
    #  Then we need rpi1 to route from veth_rpi1 to rpi1-eth0
    #       via some policy routing.
    #  Then we need rpi2 to see if it hears packets (e.g. recv_test)
    #  Then rpi2 also needs to do the policy routing, but for rpi2-eth0 to
    #   veth_rpi2.  And we need to check on our local machine if we can hear it.
    #  Then we need the packet sniffer process to listen on the veth for rpi2.
    #  So the packet sniffer, for each rpi, will need a sniffer for
    #     both the enp8s0, but also a recv thread for the corresponding veth_host



    # Create socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientSocket.bind(('10.0.0.5', 0))

    message = custom_marshall(args.message)
    # message = "hello mario".encode()

    print("Message: " + message.decode())
    # If this is from a physical node, it can be something like
    clientSocket.sendto(message, \
        ("10.0.1.5", 55000))

    # Time of sending a message
    SEND_TIMESTAMP = time.time()

    print("Sent message...")

