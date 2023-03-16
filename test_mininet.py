from mininet.net import Mininet
from mininet.node import DefaultController, OVSKernelSwitch, Node, Switch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, OVSLink, Intf, TCULink
import pdb
import time

import argparse

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

def emptyNet(host_intf):

    "Create an empty network and add nodes to it."

    net = Mininet( controller=DefaultController, link=TCLink) #, switch=OVSKernelSwitch )


    info( '*** Adding controller\n' )
    net.addController( 'c0' )

    # First, read in our config file, which tells us which hosts to add.
    f = open("config.json")
    config_data = json.load(f)
    config_data_hosts = config_data["hosts"]
    config_data_switches = config_data["switches"]
    f.close()
    
    # So here we have several different switches
    info( '*** Adding switches and links between tiers\n' )
    premise_tier_switch = net.addSwitch('pts1')
    netedge_tier_switch = net.addSwitch('nts1')
    cloud_tier_switch = net.addSwitch('cts1')
    net.addNAT(ip="10.0.0.3").configDefault()
    #  Add delays between links of those switches, to emulate the different tiers.
    net.addLink(premise_tier_switch, netedge_tier_switch, \
        delay=config_data_switches["premise-edge-delay"])
    net.addLink(netedge_tier_switch, cloud_tier_switch, \
        delay=config_data_switches["edge-cloud-delay"])
    
    network_switches = { 
        "onpremise":premise_tier_switch, 
        "edge": netedge_tier_switch, 
        "cloud": cloud_tier_switch 
    }


    

    info( '*** Adding hosts\n' )
    # Get every device, and add it as a host.  Also connect it to a switch
    #   corresponding to its tier.
    mininet_hosts = []
    pids_to_kill = []  # This is for killing the extra terminals after the simulation is done.
    for device in config_data_hosts:
        device_address = config_data_hosts[device]["ipaddr"]
        # Add it as a mininet host
        current_host = net.addHost(device, ip=device_address)
        mininet_hosts.append((current_host, config_data_hosts[device]))

        # Now, link it to the corresponding tier/switch
        device_tier = config_data_hosts[device]["location"]
        net.addLink(current_host, network_switches[device_tier])

        # Set up the veth pairs that we can use to connect listeners to this host.
        #  In the case that we have virtual devices, the veth on the host side
        #   needs to be assigned the correct IP.
        host_veth = device+"-hveth"
        device_veth = device+"-dveth"
        os.system("sudo ip link add " + host_veth + " type veth peer name " + device_veth)
        os.system("sudo ip link set " + host_veth + " up")
        os.system("sudo ip link set " + device_veth + " up")
        # In the case of a virtual address, add an IP address to a network interface
        if config_data_hosts[device]["type"] == "virtual":
            os.system("sudo ifconfig " + host_veth + " " + device_address)

        # Now move the device_veth interface into the network namespace of the mininet host
        Intf(device_veth, node=current_host)

        # Within Mininet, we need a bridged interface to connect the
        #    mininet-mininet and mininet-host interfaces
        mininet_veth = device+"-eth0" # This is automatically created by Mininet.
        current_host.cmd("ip link add br0 type bridge")
        current_host.cmd("ifconfig br0 up")
        current_host.cmd("ip link set " + mininet_veth + " master br0")
        current_host.cmd("ip link set " + device_veth + " master br0")
        

        # Load up our host processes.
        #  These run outside Mininet and communicate directly with the RPIs, and forward data
        #   to the mininet hosts
        host_pid = os.system("sudo xterm -hold -e 'sudo bash host.sh " + \
            host_veth + " " + host_intf + " " + device_address + "' &")
        pids_to_kill.append(host_pid)

    info( '*** Starting network\n')

    net.start()

    # Disable ip forwarding - prevents machines from directly contacting themselves.
    os.system("sudo sysctl -w net.ipv4.ip_forward=0")

    info( '*** Running CLI\n** \n' )

    # os.system("ifconfig ts1-eth1 " + switch_internal_address)
    
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

    parser = argparse.ArgumentParser(description='Server')
    parser.add_argument('--host_intf', type=str)
    args = parser.parse_args()

    emptyNet(args.host_intf)