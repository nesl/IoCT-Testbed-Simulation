import argparse
import socket
import threading
import time

#  This is the file that a real external client will use to send data


parser = argparse.ArgumentParser(description='Server')
# parser.add_argument('--internal_address', type=str, help='Internal mininet address')
parser.add_argument('--intermediate_address', type=str, help='')
parser.add_argument('--intermediate_port', type=int, help='')
parser.add_argument('--destination_id', type=str, help='')
parser.add_argument('--origin_id', type=str)
parser.add_argument('--message', type=str, default="hello from rpi!")
args = parser.parse_args()



LISTEN_SOCKET = None
SEND_TIMESTAMP = 0

def listen_thread():

    print("Set up listener...")

    while True:
        data, address = LISTEN_SOCKET.recvfrom(512)
        #  Example address: ('10.0.0.2', 48619)
        # If we receive something
        if len(data):
            message = data.decode()

            if "reply" in message:
                print("Time difference: %f seconds" % (time.time() - SEND_TIMESTAMP))
    

# Form the data to transmit
def custom_marshall(message, destination_id, origin_id):

    message_to_send = ':'.join([destination_id, origin_id, message])
    return message_to_send.encode()

if __name__ == '__main__':

    # Create socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = custom_marshall(args.message, args.destination_id, args.origin_id)

    print("Message: " + message.decode())
    # If this is from a physical node, it can be something like
    clientSocket.sendto(message, \
        (args.intermediate_address, args.intermediate_port ))

    # Time of sending a message
    SEND_TIMESTAMP = time.time()

    print("Sent message...")

    # LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # LISTEN_SOCKET.bind(('', 55000))
    # LISTEN_SOCKET.settimeout(10)

    # server_listen = threading.Thread(target=listen_thread)
    # server_listen.start()