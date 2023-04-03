# from mininet.net import Mininet
from mininet.node import DefaultController, OVSKernelSwitch, Node, Switch
# from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, OVSLink, Intf, TCULink

# Try out mininet wifi
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
# from mn_wifi.replaying import ReplayingMobility

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

# This goes through all of our different routers/APs/switches and sets them up
#   based on the config json
def addAllConnectors(net, connector_config):

    # This is where we append our wireless switches - they will be used again later
    wireless_connector_names = []
    #  Now, keep track of our links between different connectors
    connector_links = []
    all_connectors = {}

    # So first, go through each switch name, and set them up based on their type
    for connector_name in connector_config:

        current_connector = None
        # Get the type of this connector, and determine if it should be an AP or a switch.
        if connector_config[connector_name]["type"] == "AP":
            current_connector = net.addAccessPoint(connector_name, ssid='new-ssid', \
            mode='g', channel='1', position='45,40,0')
            net.setPropagationModel(model="logDistance", exp=4.5)
            wireless_connector_names.append(connector_name)

        elif connector_config[connector_name]["type"] == "switch":
            current_connector = net.addSwitch(connector_name)
        else:
            raise Exception("Connector type " + str(connector_name) + " unknown.")

        # Add to our links between connectors, if there is any
        if "linked_connectors" in connector_config[connector_name]:

            # Iterate through each linked connector, determine its type, and latency.
            for i, connector_destination in enumerate(connector_config[connector_name]["linked_connectors"]):
                link_type = connector_config[connector_name]["link_types"][i]
                link_latency = connector_config[connector_name]["link_latencies"][i]
                connector_links.append( (connector_name, connector_destination, link_type, link_latency) )

        # Add the connector to our dict
        all_connectors[connector_name] = current_connector

    # Iterate through each of our links and set them up
    #   Each tuple is ( connector_source, connector_destination, link type, link latency ) 

    for link_tup in connector_links:

        src_connector = all_connectors[link_tup[0]]
        dst_connector = all_connectors[link_tup[1]]
        print("LINK ADDED")
        net.addLink(src_connector, dst_connector, delay=link_tup[3])

    # Return all of the data
    return all_connectors, wireless_connector_names


# This code adds all of our hosts
def addAllHosts(net, hosts_config, external_intf, config_file, all_connectors):

    # Get every device, and add it as a host.  Also connect it to a switch
    #   corresponding to its tier.
    mininet_hosts = []
    mobility_hosts = {}
    pids_to_kill = []  # This is for killing the extra terminals after the simulation is done.
    added_netns = [] # This is a list of network namespaces we added
    for device in hosts_config:
        device_address = hosts_config[device]["mininetaddr"]
        
        current_host = None
        mininet_intf = None
        # Set up the veth pairs that we can use to connect listeners to this host.
        #  In the case that we have virtual devices, the veth on the host side
        #   needs to be assigned the correct IP.
        host_veth = device+"-hveth"
        device_veth = device+"-dveth"

        # Now, link it to the corresponding tier/connector
        device_tier = hosts_config[device]["connector_name"]

        # Again - if the device tier is on premise but is wireless, do not add a link
        # Instead, add this as a station


        if hosts_config[device]["connection_type"] == "wireless":
            
            current_host = net.addStation(device, ip=device_address, position='45,40,0')
            mininet_intf = device+"-wlan0" # This is automatically created by Mininet.
    
            mininet_hosts.append((current_host, mininet_intf, device_veth))

            # Since this is a wireless device, get the mobility data
            if "mobility" in hosts_config[device]:
                mobility_data = hosts_config[device]["mobility"]
                mobility_hosts.update({device: (current_host,mobility_data)})
        else:
            # Add it as a mininet host
            current_host = net.addHost(device, ip=device_address)
            print("LINK ADDED")
            net.addLink(current_host, all_connectors[device_tier])
            mininet_intf = device+"-eth0" # This is automatically created by Mininet.
            mininet_hosts.append((current_host, mininet_intf, device_veth))

        #  Add our veth pairs
        os.system("sudo ip link add " + host_veth + " type veth peer name " + device_veth)
        os.system("sudo ip link set " + host_veth + " up")
        os.system("sudo ip link set " + device_veth + " up")

        # In the case of a virtual address, add an IP address to a network interface
        local_ip = device_address
        use_local = False

        # If our host is virtual, then we need to create a different network namespace
        #  and execute some network configuration in that namespace
        if hosts_config[device]["type"] == "virtual":
            os.system("sudo ifconfig " + host_veth + " " + device_address)
            local_ip = hosts_config[device]["realaddr"]
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

        # So importantly, we have to check the realaddr - if it uses a local intf
        #  or a host veth or the external interface
        listening_intf = external_intf
        if local_ip == "127.0.0.1" or local_ip == "127.0.1.1":
            listening_intf = "lo"
        
        # Load up our host processes.
        #  These run outside Mininet and communicate directly with the RPIs, and forward data
        #   to the mininet hosts
        #  These only run if we have external hosts.
        if hosts_config[device]["type"] != "virtual":

            command = "sudo xterm -hold -e 'sudo bash host.sh " + \
                host_veth + " " + listening_intf + " " + device_address + " " +  \
                local_ip + " " + str(use_local) + " " + \
                config_file + "' & "
            # print(command)
            host_pid = os.system(command)
            pids_to_kill.append(host_pid)

    return mininet_hosts, mobility_hosts, pids_to_kill, added_netns


# Configure our nodes - meaning that we need to add bridges 
#   and alter some AP types if necessary
def configureAllNodes(net, mininet_hosts):

    net.configureNodes()

    # Make sure we update our bridges
    for host_data in mininet_hosts:

        # Within Mininet, we need a bridged interface to connect the
        #    mininet-mininet and mininet-host interfaces
        current_host, mininet_intf, device_veth = host_data[0], host_data[1], \
            host_data[2]
        
        # In the case of APs, we need to update 4addr, which allows it to
        #  be added to a bridge (operates in WDS mode)
        if "wlan0" in mininet_intf:
            current_host.cmd("iw dev " + mininet_intf + " set 4addr on")

        current_host.cmd("ip link add br0 type bridge")
        current_host.cmd("ifconfig br0 up")
        current_host.cmd("ip link set " + device_veth + " master br0")
        current_host.cmd("ip link set " + mininet_intf + " master br0")



# Set up our mobility experiments
# mobility_hosts is of type ( mininet_host, {"coordinates": ... , "time_interval":... } )
def configureMobility(net, mobility_hosts, wait_time):

    # Set up the mobility after configuring
    p1, p2 = {}, {}

    # Record our start and end time
    start_time = wait_time
    end_time = -1
    net.startMobility(time=0, mob_rep=1, reverse=False)

    # Iterate through each mobility host and set up the experiment
    for host_name in mobility_hosts.keys():
        mobility_host = mobility_hosts[host_name]
        host = mobility_host[0]
        coordinates = mobility_host[1]["coordinates"]
        time_interval = mobility_host[1]["time_interval"]

        host_start_time = time_interval[0] + wait_time
        host_end_time = time_interval[1] + wait_time

        # Set up coordinates
        host.coord = coordinates
        # Set start and end time
        net.mobility(host, 'start', time=host_start_time, **p1)
        net.mobility(host, 'stop', time=host_end_time, **p2)

        # Update our end time if necessary
        if host_end_time > end_time:
            end_time = host_end_time + 1

    # Finish mobility
    net.stopMobility(time=end_time)




#  This sets up our network
def InitializeNetwork(external_intf, config_file):

    WAIT_TIME = 2 # We have to wait for hosts to get set up before running certain commands

    "Create an empty network and add nodes to it."
    net = Mininet_wifi( controller=DefaultController, link=TCLink) #, switch=OVSKernelSwitch )


    info( '*** Adding controller\n' )
    main_controller = net.addController( 'c0' )

    # First, read in our config file, which tells us which hosts to add.
    f = open(config_file)
    config_data = json.load(f)
    config_data_hosts = config_data["hosts"]
    config_data_connectors = config_data["connectors"]
    f.close()
    
    # So here we have several different connectors
    info( '*** Adding connectors and links between tiers\n' )

    # Add our NAT and all of our network connectors to the network
    
    all_connectors, wireless_connector_names = \
        addAllConnectors(net, config_data_connectors)
    net.addNAT(ip="10.0.0.3").configDefault()
    
  

    info( '*** Adding hosts\n' )
    mininet_hosts, mobility_hosts, pids_to_kill, added_netns = \
        addAllHosts(net, config_data_hosts, external_intf, config_file, all_connectors)



    # Plot our graph - if we have mobile hosts
    if mobility_hosts:
        net.plotGraph(max_x=200, max_y=200)
    
    info("*** Configuring nodes\n")
    
    # Configure our nodes
    configureAllNodes(net, mininet_hosts)

    # Now, set up our mobility
    configureMobility(net, mobility_hosts, WAIT_TIME)


    info( '*** Starting network\n')

    # Start the network - do not use net.start() with mininet_wifi as it doesnt work on stations.
    net.build()
    # # Start the controller
    main_controller.start()
    # Iterate and start every switch
    for connector_name in all_connectors.keys():
        all_connectors[connector_name].start([main_controller])

    # Disable ip forwarding - prevents machines from directly contacting themselves.
    os.system("sudo sysctl -w net.ipv4.ip_forward=0")

    # Now also add additional wireless ports
    time.sleep(WAIT_TIME)  # Also make sure we wait a bit before we run anything...otherwise it will fail.
    for wireless_switch in wireless_connector_names:
        # Be sure to add the appropriate wireless interface to the OVS bridge
        interface_to_add = wireless_switch + "-wlan1.sta1"
        
        os.system("sudo ovs-vsctl add-port " + wireless_switch + " " + interface_to_add)
        #  Should be something like sudo ovs-vsctl add-port pt1 pt1-wlan1.sta1
        #  If you want to see what connections there are to each
        #   mininet bridge, do 'sudo ovs-vsctl show'



    info( '*** Running CLI\n** \n' )
    print("\n\nWhen running commands for virtual hosts,"+\
        " do not forget to begin them with 'sudo ip netns exec NS_NAME COMMAND'")
    
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

    InitializeNetwork(args.external_intf, args.config_file)