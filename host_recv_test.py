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
args = parser.parse_args()

LISTEN_SOCKET = None

# Form the data to transmit
def custom_marshall(message):

    message_to_send = message#':'.join([destination_id, origin_id, message])
    return message_to_send.encode()


def listen_thread():

    print("Set up listener...")
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        data, address = LISTEN_SOCKET.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        if len(data):
            output = Ether(data)

            protocols = output[0]
            if protocols.haslayer(UDP)and "10.0." in str(output[IP].dst):
                print(str(output[IP].src))
                print(output[IP].dst)
                print(bytes(output[UDP].payload))

                # Get the source of this packet
                message = custom_marshall("reply")
                src_address = address[0]
                # print(src_address)
                clientSocket.sendto(message, (output[IP].src, 55000))
                print("Sent reply!")



if __name__ == "__main__":

    # Set up the socket
    ETH_P_ALL=3
    LISTEN_SOCKET=socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    LISTEN_SOCKET.bind(("enp8s0", 0))
    LISTEN_SOCKET.settimeout(10)

    server_listen = threading.Thread(target=listen_thread)
    server_listen.start()