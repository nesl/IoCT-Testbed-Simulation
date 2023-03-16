#! /bin/bash

source venv/bin/activate
python host_forwarder.py --veth_intf $1 --host_intf $2 --src_ip $3