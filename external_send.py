import argparse
import socket
import threading
import time

#  This is the file that a real external client will use to send data

# EXAMPLE CALL:
#  python external_send.py --dst_ip 127.0.1.1 --dst_port 8085 --src_ip 127.0.0.1

parser = argparse.ArgumentParser(description='Server')
# parser.add_argument('--internal_address', type=str, help='Internal mininet address')
parser.add_argument('--dst_ip', type=str, help='')
parser.add_argument('--dst_port', type=int, help='')
parser.add_argument('--src_ip', type=str, help='')
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
    clientSocket.bind((args.src_ip, args.dst_port))
    # clientSocket.setsockopt(socket.SOL_SOCKET, 25, ("vclient2-hveth").encode('utf-8'))
    message = custom_marshall(args.message)
    # message = "hello mario".encode()

    print("Message: " + message.decode())
    # If this is from a physical node, it can be something like
    clientSocket.sendto(message, \
        (args.dst_ip, args.dst_port))

    # Time of sending a message
    SEND_TIMESTAMP = time.time()

    print("Sent message...")

    # LISTEN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # LISTEN_SOCKET.bind((args.src_ip, args.dst_port))
    clientSocket.settimeout(10)
    LISTEN_SOCKET = clientSocket

    server_listen = threading.Thread(target=listen_thread)
    server_listen.start()
