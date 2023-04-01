#!/usr/bin/env python

'Setting the position of nodes and providing mobility'

import sys

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.link import HostapdConfig
from mininet.link import TCLink

def topology(args):
    "Create a network."
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    h1 = net.addHost('h1', ip='10.0.0.1/8', position='100,100,0')
    sta1 = net.addStation('sta1', ip='10.0.0.2/8')
    # sta2 = net.addStation('sta2', ip='10.0.0.3/8')
    sta2 = net.addStation('sta2', mac='02:00:00:00:01:00',
                         ip='10.0.0.3/8', position='40,60,0')
    
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mode='g', channel='1',
                             position='45,40,0')
    
    # So here's what happens:
    #  sta1 is able to associate with ap1
    #  sta2, upon entering master mode, is no longer able to associate with ap1
    #    thus, it can't ping.
    #  
    
    
    c1 = net.addController('c1')

    info("*** Configuring propagation model\n")
    net.setPropagationModel(model="logDistance", exp=4.5)

    info("*** Configuring nodes\n")
    net.configureNodes()

    # ap1.setMeshMode(intf='ap1-wlan1')
    # sta2.setMasterMode(intf='sta2-wlan0')
    # ap1.setIP('10.0.0.6', intf='ap1-wlan1')
    # sta2.cmd('route add 10.0.0.2 via 10.0.0.6')
    
    info("*** Associating and Creating links\n")
    net.addLink(ap1, h1)

    # sta2 iw dev sta2-wlan0 set 4addr on
    # 


    # sta1-wlan0 
    # h1-eth0 10.0.0.1

    # Make sure all 
    # ap1.setIP('192.168.0.10/24', intf='ap1-wlan0')
    # ap1.setIP('192.168.2.1/24', intf='ap1-eth1')
    # ap2.setIP('192.168.1.10/24', intf='ap2-wlan0')
    # ap2.setIP('192.168.2.2/24', intf='ap2-eth1')
    # # Routes anything to sta2 via ap2-eth1
    # ap1.cmd('route add -net 192.168.1.0/24 gw 192.168.2.2')
    # # Routes anything to sta1 via ap1-eth1
    # ap2.cmd('route add -net 192.168.0.0/24 gw 192.168.2.1')
    
    # # For sta1, route anything to sta2 or either ap via ap1-wlan0
    # sta1.cmd('route add -net 192.168.1.0/24 gw 192.168.0.10')
    # sta1.cmd('route add -net 192.168.2.0/24 gw 192.168.0.10')

    if '-p' not in args:
        net.plotGraph(max_x=200, max_y=200)

    if '-c' in args:
        sta1.coord = ['40.0,30.0,0.0', '31.0,10.0,0.0', '31.0,30.0,0.0']
        sta2.coord = ['40.0,40.0,0.0', '55.0,31.0,0.0', '55.0,81.0,0.0']

    net.startMobility(time=0, mob_rep=1, reverse=False)

    p1, p2, p3, p4 = {}, {}, {}, {}
    if '-c' not in args:
        p1 = {'position': '40.0,30.0,0.0'}
        p2 = {'position': '40.0,40.0,0.0'}
        p3 = {'position': '31.0,10.0,0.0'}
        p4 = {'position': '55.0,31.0,0.0'}

    net.mobility(sta1, 'start', time=1, **p1)
    net.mobility(sta2, 'start', time=2, **p2)
    net.mobility(sta1, 'stop', time=12, **p3)
    net.mobility(sta2, 'stop', time=22, **p4)
    net.stopMobility(time=23)

    info("*** Starting network\n")
    net.build()
    c1.start()
    # ap1.start([c1])



    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
