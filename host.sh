#! /bin/bash

source venv/bin/activate
python host_forwarder.py --veth_intf $1 --host_intf $2 --mininetaddr $3 --realaddr $4 --use_local $5 --config_file $6
