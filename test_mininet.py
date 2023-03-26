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

def emptyNet(external_intf, config_file):

    "Create an empty network and add nodes to it."

    net = Mininet( controller=DefaultController, link=TCLink) #, switch=OVSKernelSwitch )


    info( '*** Adding controller\n' )
    net.addController( 'c0' )

    # First, read in our config file, which tells us which hosts to add.
    f = open(config_file)
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
    added_netns = [] # This is a list of network namespaces we added
    for device in config_data_hosts:
        device_address = config_data_hosts[device]["mininetaddr"]
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
        local_ip = device_address
        local_port = -1
        use_local = False
        if config_data_hosts[device]["type"] == "virtual":
            os.system("sudo ifconfig " + host_veth + " " + device_address)
            local_ip = config_data_hosts[device]["realaddr"]
            local_port = config_data_hosts[device]["serverport"]
            use_local = True

            # Also, we need to create a custom network namespace
            #  We need to move our host veth there as well 
            os.system("sudo ip netns add " + device)
            os.system("sudo ip link set " + host_veth + " netns " + device)
            os.system("sudo ip -n " + device + " link set " + host_veth + " up")
            os.system("sudo ip -n " + device + " link set lo up")
            os.system("sudo ip netns exec " + device + " ifconfig " + \
                host_veth + " " + device_address)
            added_netns.append(device)

        # Now move the device_veth interface into the network namespace of the mininet host
        Intf(device_veth, node=current_host)

        # Within Mininet, we need a bridged interface to connect the
        #    mininet-mininet and mininet-host interfaces
        mininet_veth = device+"-eth0" # This is automatically created by Mininet.
        current_host.cmd("ip link add br0 type bridge")
        current_host.cmd("ifconfig br0 up")
        current_host.cmd("ip link set " + mininet_veth + " master br0")
        current_host.cmd("ip link set " + device_veth + " master br0")


        # So importantly, we have to check the realaddr - if it uses a local intf
        #  or a host veth or the external interface
        listening_intf = external_intf
        if local_ip == "127.0.0.1" or local_ip == "127.0.1.1":
            listening_intf = "lo"
        
        # Load up our host processes.
        #  These run outside Mininet and communicate directly with the RPIs, and forward data
        #   to the mininet hosts
        #  These only run if we have external hosts.
        if config_data_hosts[device]["type"] != "virtual":

            command = "sudo xterm -hold -e 'sudo bash host.sh " + \
                host_veth + " " + listening_intf + " " + device_address + " " +  \
                local_ip + " " + str(local_port) + " " + str(use_local) + " " + \
                config_file + "' & "
            print(command)
            host_pid = os.system(command)
            pids_to_kill.append(host_pid)

    info( '*** Starting network\n')

    net.start()

    # Disable ip forwarding - prevents machines from directly contacting themselves.
    os.system("sudo sysctl -w net.ipv4.ip_forward=0")

    info( '*** Running CLI\n** \n' )
    print("\n\nWhen running commands for virtual hosts,"+\
        " do not forget to begin them with 'sudo ip netns exec NS_NAME COMMAND'")
    # os.system("ifconfig ts1-eth1 " + switch_internal_address)
    
    CLI( net )


    info( '*** Stopping network' )
    net.stop()

    # Kill the PIDs
    for pid_x in pids_to_kill:
        os.kill(int(pid_x), signal.SIGKILL)

    # Delete all the additional network namespaces
    for netns in added_netns:
        os.system("sudo ip netns delete " + netns)
    
    # Clear mininet
    os.system("mn -c")


if __name__ == '__main__':
    setLogLevel( 'info' )

    parser = argparse.ArgumentParser(description='Server')
    parser.add_argument('--external_intf', type=str)
    parser.add_argument('--config_file', type=str)
    args = parser.parse_args()

    emptyNet(args.external_intf, args.config_file)