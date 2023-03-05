import argparse
import socket
import threading
import time

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

    # Create socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # clientSocket.bind(('', 55001))
    message = custom_marshall(args.message)
    # message = "hello mario".encode()

    print("Message: " + message.decode())
    # If this is from a physical node, it can be something like
    clientSocket.sendto(message, \
        (args.destination_address, 55000))

    # Time of sending a message
    SEND_TIMESTAMP = time.time()

    print("Sent message...")

    LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    LISTEN_SOCKET.bind(('', 55000))
    LISTEN_SOCKET.settimeout(10)

    server_listen = threading.Thread(target=listen_thread)
    server_listen.start()