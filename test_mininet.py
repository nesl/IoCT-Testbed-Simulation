from mininet.net import Mininet
from mininet.node import DefaultController, OVSKernelSwitch, Node, Switch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, OVSLink, Intf, TCULink
import pdb
import time

import os
import signal
from signal import SIGKILL
import subprocess
import json

class LinuxRouter( Node ):	# from the Mininet library
    "A Node with IP forwarding enabled."

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        info ('enabling forwarding on ', self)
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()


def emptyNet():

    "Create an empty network and add nodes to it."

    net = Mininet( controller=DefaultController, link=TCLink) #, switch=OVSKernelSwitch )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )

    info( '*** Adding hosts\n' )

    # Add all hosts

    # First, read in our config file
    f = open("config.json")
    config_data = json.load(f)
    f.close()

    # Get all the data...
    switch_internal_address = config_data["switch"]["internal_ip"]

    rpi1_internal_address = config_data["rpi1"]["internal_ip"]
    rpi1_external_address = config_data["rpi1"]["external_ip"]

    rpi2_internal_address = config_data["rpi2"]["internal_ip"]
    rpi2_external_address = config_data["rpi2"]["external_ip"]

    # This are real ports on localhost
    # default_port = config_data["host"]["internal_port"] 
    # rpi1_port = config_data["rpi1"]["internal_port"]
    # rpi2_port = config_data["rpi2"]["internal_port"]

    

    # Now add our hosts...
    rpi1 = net.addHost('rpi1', ip=rpi1_internal_address)
    # rpi1 = net.addHost('rpi1', ip=rpi1_internal_address, cls=LinuxRouter, \
    #     inNamespace=False)


    

    rpi2 = net.addHost('rpi2', ip=rpi2_internal_address)
    

    h1 = net.addHost( 'h1', ip="10.0.1.8" )

    # ADD ETHERNET INTERFACE TO TS1


    # So here we have several different switches
    info( '*** Adding switches\n' )

    # Add some rules for our translator switch
    translator_switch = net.addSwitch('ts1')
    
    # translator_switch.setIP(switch_internal_address, intf="s1")

    # Here, rpi1 must be reached via rpi2
    # translator_switch.cmd("ip route add 10.0.0.2 via 10.0.0.3 dev ts1-eth1")
    # translator_switch.cmd("ip route add 172.17.15.11 via 10.0.0.2 dev ts1-eth1")

    device_tier_switch = net.addSwitch('dts1')
    netedge_tier_switch = net.addSwitch('nts1')
    cloud_tier_switch = net.addSwitch('cts1')

    # Intf( "eno1", node=rpi1 )
    # Intf( "eno1", node=rpi2 )

    info( '*** Creating links\n' )

    # Add network links (DONT FORGET YOU MUST USE TCLINKS when creating the network, not regular links!)
    # These options are under http://mininet.org/api/classmininet_1_1link_1_1TCIntf.html
    client_links = []

    # First, connect all of our tiers together
    net.addLink(translator_switch, device_tier_switch)
    net.addLink(device_tier_switch, netedge_tier_switch, delay='20ms')
    # net.addLink(netedge_tier_switch, cloud_tier_switch, delay='100ms')
    net.addLink(netedge_tier_switch, cloud_tier_switch, delay='500ms')

    # net.addLink(rpi1, rpi2, delay='100ms')

    # Now we can choose different configurations of how our RPIs are connected.
    
    # Setup1: device talks to edge
    # net.addLink(rpi1, translator_switch, delay='100ms')
    # net.addLink(rpi2, translator_switch, delay='100ms')
    # translator_switch.cmd("ip route add 10.0.0.2 via 10.0.0.2 dev ts1-eth1")
    # translator_switch.cmd("ip route add 10.0.0.3 via 10.0.0.3 dev ts1-eth1")
    
    # An RTT should be:
    #  100 + 20 + 100 + 20
    net.addLink(rpi1, device_tier_switch)
    net.addLink(rpi2, cloud_tier_switch)
    net.addLink(h1, device_tier_switch)

    # Setup2: device talks to cloud
    # An RTT should be:
    #  20 + 0 + 20 + 0
    # net.addLink(rpi1, device_tier_switch)
    # net.addLink(rpi2, netedge_tier_switch)

    net.addNAT(ip="10.0.0.3").configDefault()


    info( '*** Starting network\n')
    net.start()

    # os.system("sudo ip link add macvlan1 link enp8s0 type macvlan mode passthru")
    # os.system("sudo ip link add vlan1 link enp8s0 type macvlan mode bridge")
    # os.system("sudo ip link add vlan1 link enp8s0 type ipvlan mode l3")


    # Enable/Disable ip forwarding
    os.system("sudo sysctl -w net.ipv4.ip_forward=0") # IPv4 forwarding

    # Set up our virtual interfaces, which will get their own namespace
    # os.system("sudo ip link add vlan1 link enp8s0 type ipvlan mode l3")
    # os.system("sudo ip link set dev vlan1 up")
    # os.system("sudo ip link add vlan2 link enp8s0 type ipvlan mode l3")
    # os.system("sudo ip link set dev vlan2 up")

    # Set up some veth pairs
    os.system("sudo ip link add veth_host1 type veth peer name veth_rpi1")
    os.system("sudo ip link set veth_host1 up")
    os.system("sudo ip link set veth_rpi1 up")

    os.system("sudo ip link add veth_host2 type veth peer name veth_rpi2")
    os.system("sudo ip link set veth_host2 up")
    os.system("sudo ip link set veth_rpi2 up")
    

    # Add our routing rules
    #  Importantly, we need to route based on mac address AND source IP
    #    Basically, if mac address source is != enp8s0 and source IP is 
    #    10.0.0.5, send to veth_host1
    # ip route will not work because we need to use mac information 
    #    to differentiate incoming vs outgoing behavior
    # This can be fixed with tagging and policy based routing.


    _intf = Intf( "veth_rpi1", node=rpi1 )
    _intf2 = Intf( "veth_rpi2", node=rpi2 )
    # Add an IP address and routing policy, though in reality 
    #   this isn't necessary to receive packets.

    # os.system("sudo ip addr add 10.0.0.5 dev veth_host1")
    # os.system("sudo ip route add 10.0.1.5 dev veth_host1")
    rpi1.cmd("sudo ip addr add 10.0.1.5 dev veth_rpi1")
    rpi2.cmd("sudo ip addr add 10.0.1.6 dev veth_rpi2")
    



    # rpi1.cmd("sysctl -w net.ipv4.ip_forward=1")
    # Add some policy routing rules
    rpi1.cmd("echo 100 to_mininet >> /etc/iproute2/rt_tables")
    # Any packet that comes from 10.0.0.5 (corresponding src address) 
    #  gets sent to the rpiX-eth0 interface.

    rpi1.cmd("ip rule add fwmark 0x2 lookup to_mininet")
    rpi1.cmd("ip route add default dev rpi1-eth0 table to_mininet")
    rpi1.cmd("ip route flush cache")
    rpi1_mininet_interface = "rpi1-eth0"
    mac_address = rpi1.cmd("cat /sys/class/net/" + rpi1_mininet_interface +"/address")
    # mac_address = "dc:a6:32:c1:b6:b9" # rpi mac
    # mac_address = "9c:5c:8e:d1:f0:93" # enp8s0 mac
    print(mac_address)

    rpi1.cmd("iptables --table mangle --append INPUT --match mac --mac-source " + mac_address + " --jump MARK --set-mark 0x2")
    rpi1.cmd("iptables --table mangle --append INPUT --jump CONNMARK --save-mark")
    rpi1.cmd("iptables --table mangle --append OUTPUT --jump CONNMARK --restore-mark")


    # Note - the above approach might not work, since the actual mac is likely of enp8s0

    # Ok, so rpi1 is probably rejecting the ip packets because the Ethernet
    #  frame doesn't match so it doesn't know where to send.
    rpi1.cmd("")

    # Same thing with rpi2 - it will need to mangle the packet.

    
    





    # Load up our host processes.
    # h0_pid = translator_switch.cmd("sudo xterm -hold &")
    # translator_switch.cmd("ip route add " + rpi2_internal_address + " via " + rpi1_internal_address)
    # rpi1.cmd("ip route add " + rpi1_external_address + " via " + switch_internal_address)
    # rpi2.cmd("ip route add " + rpi2_external_address + " via " + switch_internal_address)

    # h0_pid = translator_switch.cmd("sudo xterm -hold -e 'sudo bash translator.sh " + "switch" + "' &")
    # h1_pid = rpi1.cmd("sudo xterm -hold -e 'sudo bash translator.sh " + "veth_rpi1" + "' &")
    h1_pid = os.system("sudo xterm -hold -e 'sudo bash host.sh " + \
        "veth_host1 " + rpi1_external_address + "' &")
    h2_pid = os.system("sudo xterm -hold -e 'sudo bash host.sh " + \
        "veth_host2 " + rpi2_external_address + "' &")
    
    h11_pid = rpi1.cmd("sudo xterm -hold -e 'sudo bash translator.sh " + "veth_rpi1 rpi1-eth0 " + rpi1_external_address + "' &")
    h22_pid = rpi2.cmd("sudo xterm -hold -e 'sudo bash translator.sh " + "veth_rpi2 rpi2-eth0 " + rpi2_external_address + "' &")
    # rpi1.cmd("xterm -e 'wireshark'")
    # h1_pid = rpi1.cmd("xterm -hold -e './host.sh " + rpi1_internal_address + " " + "rpi1" + "' &")
    # h2_pid = rpi2.cmd("xterm -hold -e './host.sh " + rpi2_internal_address + " " + "rpi2" + "' &")
    


    # Here we add our vlans

    

    

    # PIDS that we need to kill
    pids_to_kill = []
    # pids_to_kill.append(h1_pid.split()[-1])
    # pids_to_kill.append(h2_pid.split()[-1])

    info( '*** Running CLI\n  DO NOT FORGET THE ADDITIONAL COMMAND FOR TS1** \n' )
    # net.cmd("ts1 ifconfig ts1-eth1 10.0.0.1")

    
    # os.system("ifconfig ts1-eth1 " + switch_internal_address)
    
    CLI( net )


    # YOU HAVE TO ISSUE THIS COMMAND WHEN MININET IS RUNNING
    #  This allows 
    # ts1 ifconfig ts1-eth1 10.0.0.7

    info( '*** Stopping network' )
    net.stop()

    # Kill the PIDs
    for pid_x in pids_to_kill:
        os.kill(int(pid_x), signal.SIGKILL)
    
    # Clear mininet
    os.system("mn -c")

    # Remove veth pairs
    
    # Set 
    # os.system("sudo ip link set enp8s0 nomaster")

if __name__ == '__main__':
    setLogLevel( 'info' )
    emptyNet()