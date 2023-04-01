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

def emptyNet(external_intf, config_file):

    "Create an empty network and add nodes to it."

    net = Mininet_wifi( controller=DefaultController, link=TCLink) #, switch=OVSKernelSwitch )


    info( '*** Adding controller\n' )
    main_controller = net.addController( 'c0' )

    # First, read in our config file, which tells us which hosts to add.
    f = open(config_file)
    config_data = json.load(f)
    config_data_hosts = config_data["hosts"]
    config_data_switches = config_data["switches"]
    f.close()
    
    # So here we have several different switches
    info( '*** Adding switches and links between tiers\n' )


    wireless_switches = []
    # Check the switch types:
    premise_tier_switch = None
    if config_data_switches["premise-type"] == "wireless":
        premise_tier_switch = net.addAccessPoint('pts1', ssid='new-ssid', \
            mode='g', channel='1', position='45,40,0')
        # Also add propagation model
        net.setPropagationModel(model="logDistance", exp=4.5)
        wireless_switches.append('pts1')
    else:
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
    mobility_hosts = []
    pids_to_kill = []  # This is for killing the extra terminals after the simulation is done.
    added_netns = [] # This is a list of network namespaces we added
    for device in config_data_hosts:
        device_address = config_data_hosts[device]["mininetaddr"]
        
        
        current_host = None
        mininet_intf = None
        # Set up the veth pairs that we can use to connect listeners to this host.
        #  In the case that we have virtual devices, the veth on the host side
        #   needs to be assigned the correct IP.
        host_veth = device+"-hveth"
        device_veth = device+"-dveth"

        # Now, link it to the corresponding tier/switch
        device_tier = config_data_hosts[device]["location"]
        # Again - if the device tier is on premise but is wireless, do not add a link
        # Instead, add this as a station
        if device_tier == "onpremise" and config_data_switches["premise-type"] == "wireless":
            
            # current_host = net.addHost(device, ip=device_address)
            # net.addLink(current_host, network_switches[device_tier])
            # mininet_intf = device+"-eth0" # This is automatically created by Mininet.


           
            current_host = net.addStation(device, ip=device_address, position='45,40,0')
            
            mininet_intf = device+"-wlan0" # This is automatically created by Mininet.
    
            mininet_hosts.append((current_host, mininet_intf, device_veth))
            mobility_hosts.append(current_host)
        else:
            # Add it as a mininet host
            current_host = net.addHost(device, ip=device_address)
            
            net.addLink(current_host, network_switches[device_tier])
            mininet_intf = device+"-eth0" # This is automatically created by Mininet.
            mininet_hosts.append((current_host, mininet_intf, device_veth))

        
        #  Add our veth pairs
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

    # Start the mobility
    net.plotGraph(max_x=100, max_y=100)
    
    info("*** Configuring nodes\n")
    net.configureNodes()

    # Make sure we update our bridges
    for host_data in mininet_hosts:

        # Within Mininet, we need a bridged interface to connect the
        #    mininet-mininet and mininet-host interfaces
        current_host, mininet_intf, device_veth = host_data[0], host_data[1], host_data[2]
        
        

        # First, check to see if we need to run this host in master mode 
        # if "wlan0" in mininet_intf:
        #     print(host_data)
        #     # asdf
        #     current_host.setMasterMode(intf=mininet_intf, \
        #         ssid=mininet_intf+"-ssid", channel='2', mode='n2')
        
        if "wlan0" in mininet_intf:
            current_host.cmd("iw dev " + mininet_intf + " set 4addr on")



        current_host.cmd("ip link add br0 type bridge")
        current_host.cmd("ifconfig br0 up")
        current_host.cmd("ip link set " + device_veth + " master br0")
        current_host.cmd("ip link set " + mininet_intf + " master br0")

    


    # Set up the mobility after configuring
    p1, p2, p3, p4 = {}, {}, {}, {}
    
    # net.setMobilityModel(time=0, model='RandomDirection',
    #                 max_x=200, max_y=200, seed=20)

    mobility_hosts[0].coord = ['40.0,30.0,0.0', \
        '15.0,15.0,0.0', '130.0,20.0,0.0', '40.0,30.0,0.0']
    net.startMobility(time=0, mob_rep=1, reverse=False)
    net.mobility(mobility_hosts[0], 'start', time=2, **p1)
    net.mobility(mobility_hosts[0], 'stop', time=50, **p2)
    net.stopMobility(time=50)
    


    info( '*** Starting network\n')

    # Start the network - do not use net.start() with mininet_wifi as it doesnt work on stations.
    net.build()
    # # Start the controller
    main_controller.start()
    # Iterate and start every switch
    for switchname in network_switches.keys():
        network_switches[switchname].start([main_controller])

    # Disable ip forwarding - prevents machines from directly contacting themselves.
    os.system("sudo sysctl -w net.ipv4.ip_forward=0")

    # Now also add additional wireless ports
    # For our switches, check to see if we need to add any ports to OVS
    # time.sleep(5)
    for wireless_switch in wireless_switches:
        # Be sure to add the appropriate wireless interface to the OVS bridge
        interface_to_add = wireless_switch + "-wlan1.sta1"
        # os.system("sudo ovs-vsctl add-port " + wireless_switch + " " + interface_to_add)
        #  Should be something like sudo ovs-vsctl add-port pts1 pts1-wlan1.sta1

    # ReplayingMobility(net)


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