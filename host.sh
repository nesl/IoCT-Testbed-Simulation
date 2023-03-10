#! /bin/bash

source venv/bin/activate
# python host.py --device_id $1
# python host.py --ip $1 --device_id $2
python host_forwarder.py --veth_intf $1 --src_ip $2