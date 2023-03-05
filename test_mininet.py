from mininet.net import Mininet
from mininet.node import DefaultController, OVSKernelSwitch, Node, Switch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, OVSLink, Intf
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

    net = Mininet( controller=DefaultController, link=TCLink, switch=OVSKernelSwitch )

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
    rpi1 = net.addHost('rpi1', ip=rpi1_internal_address, cls=LinuxRouter)
    # rpi1.cmd('arp -s ' + config_data["switch"]["internal_ip"] + ' fe80::f09b:adff:fe76:90ea')
    

    # rpi1.cmd("ip route add 10.0.0.5 via 10.0.0.2 dev rpi1-eth1")
    rpi2 = net.addHost('rpi2', ip=rpi2_internal_address, cls=LinuxRouter)
    # rpi2.cmd('arp -s ' + config_data["switch"]["internal_ip"] + ' fe80::f09b:adff:fe76:90ea')
    

    h1 = net.addHost( 'h1', ip="10.0.1.8" )
    # h2 = net.addHost( 'h2', ip=rpi2_internal_address )
    # h2 = net.addHost( 'h2', ip=rpi1_internal_address )
    # h3 = net.addHost( 'h3', ip=rpi2__internal_address )

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
    net.addLink(netedge_tier_switch, cloud_tier_switch, delay='100ms')

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

    # Load up our host processes.
    # h0_pid = translator_switch.cmd("sudo xterm -hold &")
    translator_switch.cmd("ip route add " + rpi2_internal_address + " via " + rpi1_internal_address)
    rpi1.cmd("ip route add " + rpi1_external_address + " via " + switch_internal_address)
    rpi2.cmd("ip route add " + rpi2_external_address + " via " + switch_internal_address)

    h0_pid = translator_switch.cmd("sudo xterm -hold -e 'sudo bash translator.sh " + "switch" + "' &")
    h1_pid = rpi1.cmd("xterm -hold -e './host.sh " + "rpi1" + "' &")
    h2_pid = rpi2.cmd("xterm -hold -e './host.sh " + "rpi2" + "' &")
    

    # PIDS that we need to kill
    pids_to_kill = []
    # pids_to_kill.append(h1_pid.split()[-1])
    # pids_to_kill.append(h2_pid.split()[-1])

    info( '*** Running CLI\n  DO NOT FORGET THE ADDITIONAL COMMAND FOR TS1** \n' )
    # net.cmd("ts1 ifconfig ts1-eth1 10.0.0.1")

    os.system("sudo sysctl -w net.ipv4.ip_forward=0") # Disable IPv4 forwarding
    os.system("ifconfig ts1-eth1 " + switch_internal_address)

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
    	

if __name__ == '__main__':
    setLogLevel( 'info' )
    emptyNet()