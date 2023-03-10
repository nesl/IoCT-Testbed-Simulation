
source venv/bin/activate
# sudo python translator.py --device_id $1
sudo python host_recv_test.py --veth_intf $1 --mininet_intf $2 --internal_ip $3