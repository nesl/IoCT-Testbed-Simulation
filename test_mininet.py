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
    

def emptyNet():

    "Create an empty network and add nodes to it."

    net = Mininet( controller=DefaultController, link=TCLink )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )

    info( '*** Adding hosts\n' )

    # Add all hosts

    host_address = '10.0.0.1'
    rpi1_address = '10.0.0.2'
    rpi2_address = '10.0.0.3'

    host_port = 55000 # This is a real port on localhost
    rpi1_port = 55001

    h1 = net.addHost( 'h1', ip=host_address )
    h2 = net.addHost( 'h2', ip=rpi1_address )
    h3 = net.addHost( 'h3', ip=rpi2_address )

    info( '*** Adding switch\n' )
    s1 = net.addSwitch( 's1' )
    # Intf('wlp6s0', node=s1)

    info( '*** Creating links\n' )

    # Add network links (DONT FORGET YOU MUST USE TCLINKS, not regular links!)
    # These options are under http://mininet.org/api/classmininet_1_1link_1_1TCIntf.html
    client_links = []
    net.addLink(h1, s1)
    # net.addLink(h2, s1, delay='1s')
    net.addLink(h2, s1)
    net.addLink(h3, s1)

    net.addNAT().configDefault()


    info( '*** Starting network\n')
    net.start()


    # Load up our host processes.
    h1_pid = h1.cmd("xterm -hold -e './host.sh " + str(host_address) + \
            " " + str(host_port) + "' &")

    time.sleep(2)

    h2_pid = h2.cmd("xterm -hold -e './host.sh " + str(rpi1_address) + \
            " " + str(rpi1_port) + "' &")

    #ZMQ brokers
    # 
    # h3_pid = h3.cmd("xterm -hold -e './broker.sh " + str(broker_2_port_consumers) + " " + str(broker_2_port_producers) + "' &")



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