
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

## Setup of virtual devices

When we say 'virtual devices', we really mean processes which are executed on the local machine, but appear to be an external device.  So for example, we want a python process to appear like it is in a different physical device than the current host.  This is accomplished by Linux network namespaces - basically, a virtual device is a separate network namespace, and in our case, can only interact with other devices via veth interfaces.  This allows us to avoid the issue of multiple local processes interacting directly rather than via Mininet, which is often the goal when attempting to simulate network latencies between different processes despite them residing on the same machine.

## Manging the Configurations

So the primary way we set up our experiments is via the 'config.json' file.
The general format of each entry is as follows:

name_of_device:     # This is just for naming our device
    realaddr:         # This is the ip address of the process or physical device.  In the case of physical devices, it is coincidentally the same address we will use in Mininet.  However, it is also possible to have a different address here than the mininet address (e.g. you have a process running 127.0.0.1)
    mininetaddr:   # This is the IP address used by Mininet
    type:           # This is the type of device, either "physical" or "virtual".  Based on this entry, the system determines what interface it listens and transmits data on.
    location:       # This entry determines the network behavior of messages sent across mininet, with options of 'onpremise', 'edge', or 'cloud'.  For example, communication between a device at 'onpremise' and a device at 'cloud' will incur a greater network latency than 'onpremise' and 'edge'.

# Running the simulation

## Commands

```
sudo python test_mininet.py  --external_intf INTERFACE_NAME --config_file CONFIG_LOCATION
```
The --external_intf argument is the physical network interface that you are using to connect to the other external devices.  The config file stores the settings for the experiment.  For example, if your physical interface is called "enp8s0" and your config file is at "tests/mpc_test/mpc_config.json", then this command would be:
```
sudo python test_mininet.py  --external_intf enp8s0 --config_file tests/mpc_test/mpc_config.json
```

### IMPORTANT NOTE:
You should rerun this command anytime you make changes to the config file!


## Notes on virtual hosts

When you have some processes that you wish to execute locally yet still make use of the simulated network of Mininet, you can achieve this by executing them in their corresponding network namespace.  The folder 'tests/mpc_test/mpc_config.json' gives an example configuration - it sets up two different virtual devices, vclient1 and vclient2.  The simulator also sets up two network namespaces for each virtual device (or more specifically, for every entry which has the "type"=="virtual"), and the names of each namespace is the same as the device name.  You can run python scripts in each namespace in the following way:

```
sudo ip netns exec NS_NAME python PYTHON_SCRIPT
```
where NS_NAME refers to a device name like 'vclient1' in the case of tests/mpc_test/mpc_config.json, and PYTHON_SCRIPT can be any python script that you want to use as a client/server.  For example:
```
sudo ip netns exec vclient1 python tests/simple_reply_test/external_recv.py --src_ip 10.0.0.11 --src_port 8085
```
is an example usage of one of our test scripts.


## Some quick tests

### Pre-flight checks
Firstly, if you have two external devices which are connected via the mininet host machine, then you should test to see if they communicate via this host.  These external devices should not be able to communicate if the simulation is off, and should be able to communicate once the simulation is active.  You can easily check this via ping commands.

### Simple send and receive

Once the simulation is up and running, you can quickly check communication between any two devices. First, run the following command on an external device that listens to messages (assuming you send the file there)
```
python tests/simple_reply_test/external_recv.py --src_ip IP_ADDR --src_port DESIRED_PORT
```
and run the following command on another device that sends messages
```
python tests/simple_reply_test/external_send.py --dst_ip DEST_IP_ADDR --dst_port DESIRED_PORT --src_ip IP_ADDR
```
where IP_ADDR is the physical address of the current listening device.  This should match the 'ipaddr' field in the config.json.  DEST_IP_ADDR is the ip address of the other device using external_recv.  DESIRED_PORT in both external_recv.py and external_send.py should match.

### Simple HTTP access

You can also see if you can access HTTP servers via this simulation.  Assuming the same setup (two external devices), have one act as an HTTP server and another as a client.  On the server, you should run:
```
python3 -m http.server
```
And on the client, you can open a web browser to connect to that server.

### Simple SSH access

You can also see if you can ssh from one external device into another via ssh, and it should reflect some of the latency characteristics of your simulation (e.g. typing into the ssh terminal updates with a slight delay) This example, as well as the above HTTP access, is meant to show that unmodified applications can communicate via this simulation. 

### Testing with some control scenarios:

You can try out some of the code for robotic control and the impact of latency on those scenarios.  To use the code, you will need to run a few commands.  First you will need to run the mininet simulation:
```
sudo python test_mininet.py  --external_intf enp8s0 --config_file tests/mpc_test/mpc_config.json
```
Then you should run the 'server' code to begin waiting for input:
```
sudo ip netns exec vclient1 python tests/mpc_test/mpc_socket_lc_cloud.py
```

Then you should run the 'client' code to send input and log results:
```
sudo ip netns exec vclient2 python tests/mpc_test/start_script_socket.py
```


### Testing with simple mobility:
```
sudo ovs-vsctl add-port pts1 pts1-wlan1.sta1
```


# Quick Issues

## For some reason, I'm getting multiple 'copies' of a message between two external devices!

It's likely that your system still have IPv4 forwarding turned on.  Make sure it is turned off.  Normally, this is automatically handled in our simulation but sometimes another privileged process may turn it back on.

## Attempting to start the simulation causes some error like "Error creating interface pair"

This just means Mininet did not exit properly, so it needs to be cleaned up:
```
sudo mn -c
```