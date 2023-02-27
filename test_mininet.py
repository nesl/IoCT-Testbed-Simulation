from mininet.net import Mininet
from mininet.node import DefaultController, OVSKernelSwitch
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



def emptyNet():

    "Create an empty network and add nodes to it."

    net = Mininet( controller=DefaultController, link=TCLink)#, switch=OVSKernelSwitch )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )

    info( '*** Adding hosts\n' )

    # Add all hosts

    # First, read in our config file
    f = open("config.json")
    config_data = json.load(f)
    f.close()

    # Get all the data...
    host_internal_address = config_data["host"]["internal_ip"]
    rpi1_internal_address = config_data["rpi1"]["internal_ip"]
    rpi1_external_address = config_data["rpi1"]["external_ip"]

    rpi2_internal_address = config_data["rpi2"]["internal_ip"]
    rpi2_external_address = config_data["rpi2"]["external_ip"]

    # This are real ports on localhost
    default_port = config_data["host"]["internal_port"] 
    rpi1_port = config_data["rpi1"]["internal_port"]
    rpi2_port = config_data["rpi2"]["internal_port"]


    # Now add our hosts...
    rpi1 = net.addSwitch('rpi1', ip=rpi1_internal_address)
    rpi2 = net.addSwitch('rpi2', ip=rpi2_internal_address)

    # h1 = net.addHost( 'h1', ip=rpi1_internal_address )
    # h2 = net.addHost( 'h2', ip=rpi2_internal_address )
    # h2 = net.addHost( 'h2', ip=rpi1_internal_address )
    # h3 = net.addHost( 'h3', ip=rpi2__internal_address )



    # So here we have several different switches
    info( '*** Adding switches\n' )

    device_tier_switch = net.addSwitch('dts1')
    netedge_tier_switch = net.addSwitch('nts1')
    cloud_tier_switch = net.addSwitch('cts1')

    # Intf( "h1-eth0", node=rpi1 )
    # Intf( "h2-eth0", node=rpi2 )

    info( '*** Creating links\n' )

    # Add network links (DONT FORGET YOU MUST USE TCLINKS when creating the network, not regular links!)
    # These options are under http://mininet.org/api/classmininet_1_1link_1_1TCIntf.html
    client_links = []

    # First, connect all of our tiers together
    net.addLink(device_tier_switch, netedge_tier_switch, delay='15ms')
    net.addLink(netedge_tier_switch, cloud_tier_switch, delay='50ms')


    # Now we can choose different configurations of how our RPIs are connected.
    
    # Setup1: device talks to edge
    net.addLink(rpi1, device_tier_switch, delay='1s')
    net.addLink(rpi2, netedge_tier_switch, delay='1s')
    # net.addLink(h1, device_tier_switch, cls=TCLink, delay='1s')
    # net.addLink(h2, cloud_tier_switch)

    # Setup2: device talks to cloud
    # net.addLink(rpi1, device_tier_switch)
    # net.addLink(rpi2, cloud_tier_switch)




    net.addNAT().configDefault()


    info( '*** Starting network\n')
    net.start()

    # Load up our host processes.
    h1_pid = rpi1.cmd("xterm -hold -e './host.sh " + "rpi1" + "' &")

    h2_pid = rpi2.cmd("xterm -hold -e './host.sh " + "rpi2" + "' &")
    

    # PIDS that we need to kill
    pids_to_kill = []
    # pids_to_kill.append(h1_pid.split()[-1])
    # pids_to_kill.append(h2_pid.split()[-1])

    info( '*** Running CLI\n' )
    CLI( net )

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