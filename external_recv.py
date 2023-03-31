import argparse
import socket
import threading
# import IN

#  This is the file that a real external client will use to send data

# Example usage:
#  python external_recv.py --src_ip 127.0.1.1 --src_port 8085

parser = argparse.ArgumentParser(description='Server')
parser.add_argument('--src_port', type=int, help='')
parser.add_argument('--src_ip', type=str, help='')
args = parser.parse_args()

LISTEN_SOCKET = None

# Form the data to transmit
def custom_marshall(message):

    message_to_send = message #':'.join([destination_id, origin_id, message])
    return message_to_send.encode()


def listen_thread():

    print("Set up listener...")
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # clientSocket.bind(("127.0.1.1", 0))

    while True:
        data, address = LISTEN_SOCKET.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        if len(data):
            print(data)
            # Make sure you get the counter
            msg_index = data.decode().split(":")[1]

            # Get the source of this packet
            message = custom_marshall("reply:"+msg_index)
            src_address = address[0]
            src_port = address[1]
            print(message)
            LISTEN_SOCKET.sendto(message, (address[0], args.src_port))
            print("Sent reply!")




if __name__ == "__main__":

    # Set up the socket
    LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # LISTEN_SOCKET = socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM)
    # ETH_P_ALL=3 # not defined in socket module, sadly...
    # LISTEN_SOCKET=socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    # LISTEN_SOCKET.bind(("enp8s0", 0))
    # LISTEN_SOCKET.bind((0,-1))
    # LISTEN_SOCKET.setsockopt(socket.SOL_SOCKET, 25, ("enp8s0").encode('utf-8'))
    LISTEN_SOCKET.bind((args.src_ip, args.src_port))
    # LISTEN_SOCKET.setsockopt(socket.SOL_SOCKET, 25, ("vclient1-hveth").encode('utf-8'))
    LISTEN_SOCKET.settimeout(10)

    server_listen = threading.Thread(target=listen_thread)
    server_listen.start()
