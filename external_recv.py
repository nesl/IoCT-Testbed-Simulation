import argparse
import socket
import threading

#  This is the file that a real external client will use to send data


parser = argparse.ArgumentParser(description='Server')
# parser.add_argument('--internal_address', type=str, help='Internal mininet address')
parser.add_argument('--intermediate_address', type=str, help='')
parser.add_argument('--intermediate_port', type=int, help='')
# parser.add_argument('--destination_address', type=str, help='')
# parser.add_argument('--destination_port', type=int, help='')
parser.add_argument('--origin_id', type=str)
args = parser.parse_args()

LISTEN_SOCKET = None
ORIGIN_ID = args.origin_id

# Form the data to transmit
def custom_marshall(message, destination_id, origin_id):

    message_to_send = ':'.join([destination_id, origin_id, message])
    return message_to_send.encode()


def listen_thread():

    print("Set up listener...")
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        data, address = LISTEN_SOCKET.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        if len(data):
            print(data.decode())

            # Get the source of this packet
            source_id = data.split(":")[1]
            message = custom_marshall("reply", source_id, ORIGIN_ID)

            clientSocket.sendto(message, \
                (args.intermediate_address, args.intermediate_port ))



if __name__ == "__main__":

    # Set up the socket
    LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    LISTEN_SOCKET.bind(('', 55000))
    LISTEN_SOCKET.settimeout(10)

    server_listen = threading.Thread(target=listen_thread)
    server_listen.start()