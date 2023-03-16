
# Introduction


# Setup

## Setup of physical devices

In order to make use of our Mininet simulation, physical devices which are external to the host running the simulation must route through the host.
For example, a Raspberry Pi wanting to communicate with another Raspberry Pi via our simulation must route their traffic through our host.  This is relatively easy to do - just run the following command in each external device.
```
ip route SUBNET via HOST_IP
```
This is assuming your devices are all sitting on the same subnet.  If your subnet is 10.0.0.0/24 and your host running Mininet is on 10.0.0.7, then this command would be:
```
ip route 10.0.0.0/24 via 10.0.0.7
```

On your host machine, make sure your IP forwarding is turned OFF.
```
sysctl -w net.ipv4.ip_forward 
```
This should print 0 if it is turned off.

## Manging the Configurations

So the primary way we set up our experiments is via the 'config.json' file.
The general format of each entry is as follows:

name_of_device:     # This is just for naming our device
    ipaddr:         # This is the ip address of the process or physical device.  It is also coincidentally the same address we will use in Mininet.
    type:           # This is the type of device, either "physical" or "virtual".  Based on this entry, the system determines what interface it listens and transmits data on.
    location:       # This entry determines the network behavior of messages sent across mininet, with options of 'onpremise', 'edge', or 'cloud'.  For example, communication between a device at 'onpremise' and a device at 'cloud' will incur a greater network latency than 'onpremise' and 'edge'.

# Running the simulation

## Commands

```
sudo python test_mininet.py  --host_intf INTERFACE_NAME
```
The --host_intf argument is the physical network interface that you are using to connect to the other external devices.  For example, if your physical interface is called "enp8s0", then this command would be:
```
sudo python test_mininet.py  --host_intf enp8s0
```


## Some quick tests
Once the simulation is up and running, you can quickly check communication between any two devices. First, run the following command on an external device that listens to messages (assuming you send the file there)
```
python external_recv.py
```
and run the following command on another device that sends messages
```
python external_send.py --destination_address IP_ADDR
```
where IP_ADDR is the physical address of the listening device.  This should match the 'ipaddr' field in the config.json


# Quick Issues

## For some reason, I'm getting multiple 'copies' of a message between two external devices!

It's likely that your system still have IPv4 forwarding turned on.  Make sure it is turned off.  Normally, this is automatically handled in our simulation but sometimes another privileged process may turn it back on.

## Attempting to start the simulation causes some error like "Error creating interface pair"

This just means Mininet did not exit properly, so it needs to be cleaned up:
```
sudo mn -c
```