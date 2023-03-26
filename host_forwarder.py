import argparse
import socket
import threading
from scapy.all import *
import json
# from getmac import get_mac_address
# import IN

#  This is the file that a real external client will use to send data
import psutil


def get_mac_address(intf_name):
    mac_address = ""
    for interface, snics in psutil.net_if_addrs().items():
        if intf_name == interface:
            # Get the mac address
            for snic in snics:
                if snic.family == socket.AF_PACKET:
                    mac_address = snic.address
                    break
    return mac_address


#  Translate an ip address to its goal type ("mininetaddr" or "realaddr")
def translate_address(ipaddr, current_type, goal_type, config_data):

    translated_address = ""
    # Look for the ip addr in the config data
    for host in config_data["hosts"]:
        host_data = config_data["hosts"][host]
        if host_data[current_type] == ipaddr:
            translated_address = host_data[goal_type]
            break
    return translated_address


# Create a spoofed packet with new ips
def create_spoofed_packet(pkt, new_src_ip, new_dst_ip):

    eth_src = pkt[Ether].src
    eth_dst = pkt[Ether].dst
    # print(pkt[Ether].dst)

    # Get the src and dst ports for the packets
    #  Set them up again
    pkt[IP].src = new_src_ip
    pkt[IP].dst = new_dst_ip

    # Also, don't foget the checksumming stuff
    del pkt[IP].chksum
    if pkt.haslayer(TCP):
        del pkt[TCP].chksum
    elif pkt.haslayer(UDP):
        del pkt[UDP].chksum
    pkt = pkt.__class__(bytes(pkt))  # Recreate the packet with new checksum


    #Just avoid the localhost mac address since the packet will get stuck
    #  once it enters another network namespace
    pkt[Ether].src = "26:a9:d9:26:a9:d9" 
    pkt[Ether].dst = "26:a9:d9:26:a9:d8"

    return pkt

# There's some cases where we have to translate addresses - for example,
#   when we have a local process that we want to use with mininet
#   But these use the localhost addresses, so we HAVE to perform translation
#   which requires looking up the corresponding mininet address.
def translate_packet_to_mininet(pkt, config_data):

    # First, we have to get the src and dst ip addresses, which are in 'real' ips
    src_ip = str(pkt[IP].src)
    dst_ip = str(pkt[IP].dst)

    print(src_ip)
    print(dst_ip)

    new_src_ip = translate_address(src_ip, "realaddr", "mininetaddr", config_data)
    new_dst_ip = translate_address(dst_ip, "realaddr", "mininetaddr", config_data)

    print(pkt)

    pkt = create_spoofed_packet(pkt, new_src_ip, new_dst_ip)
    return pkt


def translate_packet_to_real(pkt, config_data):
    # First, we have to get the src and dst ip addresses, which are in 'real' ips
    src_ip = str(pkt[IP].src)
    dst_ip = str(pkt[IP].dst)
    print(src_ip)
    print(dst_ip)
    new_src_ip = translate_address(src_ip, "mininetaddr", "realaddr", config_data)
    new_dst_ip = translate_address(dst_ip, "mininetaddr", "realaddr", config_data)

    pkt = create_spoofed_packet(pkt, new_src_ip, new_dst_ip)
    return pkt

#  This gets a packet on enp8s0 and forwards it to the veth interface
#  If you want to pass data to this function, you have to use its nested form
def forward_internal(veth_intf, config_data, use_local):
    
    def forward(pkt):
        print("\nSending data to internal host:")
        print(pkt[Ether].src)
        print(pkt[Ether].dst)
        # if use_local:
        #     pkt = translate_packet_to_mininet(pkt, config_data)
        # print(pkt[Ether].src)
        # print(pkt[Ether].dst)

        # print("Forwarding to " + str(veth_intf))
        print(pkt.summary())
        sendp(pkt, iface=veth_intf)

    return forward


# Meant to send to physical interface and out to rpi
def forward_external(config_data, use_local):

    def forward(pkt):

        print("\nSending data to external host:")
        print(pkt.summary())

        # if use_local:
        #     pkt = translate_packet_to_real(pkt, config_data)

        # Sending from source enp8s0 and dstination of the rpi
        # spoofed_packet = Ether(src="9c:5c:8e:d1:f0:93", dst="dc:a6:32:c1:f1:9f") / IP(src=dst_ip, \
        #             dst=src_ip) \
        #             / UDP(sport=55000, dport=55000) / "reply".encode()
        # print(pkt.summary())
        # print(pkt[Ether].src)
        # print(pkt[Ether].dst)
        send(pkt.payload)

    return forward


# Listens on enp8s0
# MAKE SURE WE DO NOT LISTEN TO OUR OWN SRC MAC
def forward_to_mininet(host_intf, src_ip, veth_intf, use_local, \
    local_port, config_data):

    # Create socket

    print("Start listening on " + host_intf + \
        " with IP " + str(src_ip) + " with port " + str(local_port))
    # Source IP should match this host

    mac_addr = get_mac_address(host_intf)
    # filter='src host ' + src_ip + ' and not ether src host ' + mac_addr + \
    # ' and not src port 22'
    filter='src host ' + src_ip + ' and not ether src host ' + mac_addr
    #  If we are using the localhost, then we have to filter by port, not mac addr


    # if use_local:  # We only read if the mac address is for lo
    #     lo_mac_addr = "00:00:00:00:00:00"
    #     broadcast_mac_addr = "ff:ff:ff:ff:ff:ff"
        
    #     filter = None
    #     # If this is a client, then we filter based on the dst port
    #     if local_port == -1:  # This means we filter on dst port instead. This is used by the client.
    #         print("\nFilter as client\n")
    #         filter = 'src host ' + src_ip + ' and dst port ' + str(8085) + \
    #             ' and ether src host ' + lo_mac_addr + ' and not ether dst host ' + \
    #             broadcast_mac_addr
    #         filter = 'src host ' + src_ip + ' and dst port ' + str(8085)
    #     else:  # If this is a server, we make sure the IP matches...
    #         #  This filter is used by the server
    #         print("\nFilter as server\n")
    #         # filter = 'src host ' + src_ip + ' and ether dst host ' + lo_mac_addr + \
    #         #     ' and not dst port ' + str(8085) + ' and not icmp'
    #         filter = 'src host ' + src_ip + ' and not dst port ' + \
    #             str(local_port) + ' and not icmp'
    #         filter = 'src host ' + src_ip + ' and not dst port ' + \
    #             str(local_port) + ' and dst net 10.0.0.0/24'

    print("Filter to internal: " + filter)
    sniff(iface=host_intf, filter=filter, \
        prn=forward_internal(veth_intf, config_data, use_local))


# Listen on destination (veth) - this sends to physical or virtual hosts
def forward_to_external_host(veth_intf, src_ip, config_data):
    # Create socket

    print("Start listening on " + veth_intf + \
        " with IP " + str(src_ip))
    # filter='dst host ' + args.src_ip + ' and dst port 55000'
    # Destination IP should  match this host
    filter='dst host ' + src_ip
    print("Filter to external: " + filter)
    sniff(iface=veth_intf, filter=filter, \
        prn=forward_external(config_data, use_local))



if __name__ == "__main__":

    # Parse the arguments
    parser = argparse.ArgumentParser(description='Server')
    parser.add_argument('--veth_intf', type=str)
    parser.add_argument('--host_intf', type=str)
    parser.add_argument('--mininetaddr', type=str)
    parser.add_argument('--realaddr', type=str)
    parser.add_argument('--local_port', type=int)
    parser.add_argument('--use_local', type=str)
    parser.add_argument('--config_file', type=str)
    args = parser.parse_args()

    # Open our config file, and pass it along.
    f = open(args.config_file)
    config_data = json.load(f)
    f.close()

    # Note - the behavior of this host code changes depending on if
    #   this node is physical or virtual
    #  If this is meant to represent a physical node, then it is given a 'real' IP
    #    like 10.0.0.6, and it uses the src_ip as its listening address
    #  If this is meant to represent a virtual node, then it is given the lo IP
    #    which is 127.0.1.1
    external_ip = args.realaddr
    mininet_ip = args.mininetaddr
    use_local = args.use_local == "True"

    # Listening for external IP calls
    # Important note - 
    #  If our virtual process is already listening on an interface, 
    #   we do not need ANY forwarding (we already have a server on this intf)
    # if use_local and mininet_ip != external_ip:

    server_listen = threading.Thread(target=forward_to_mininet, \
        args=(args.host_intf, external_ip, args.veth_intf, \
            use_local, args.local_port, config_data))
    server_listen.start()

    # Listening for mininet IP calls
    server_listen2 = threading.Thread(target=forward_to_external_host, \
        args=(args.veth_intf,mininet_ip, config_data))
    server_listen2.start()