#! /bin/bash

source venv/bin/activate
python host_forwarder.py --veth_intf $1 --host_intf $2 --mininetaddr $3 --realaddr $4 --local_port $5 --use_local $6 --config_file $7