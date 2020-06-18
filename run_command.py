#!/usr/bin/python3

import pyeapi
import argparse
import ssl
import ipaddress

try:
  _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
# Legacy Python that doesn't verify HTTPS certificates by default
  pass
else:
# Handle target environment that doesn't support HTTPS verification
  ssl._create_default_https_context = _create_unverified_https_context

parser = argparse.ArgumentParser()
parser.add_argument('--conf', required=False, action='append',
                    default=[], help='Config to apply to all switches')
parser.add_argument('--interface', required=False,
                    default='', help='Interface to configure')
parser.add_argument('--addr', required=False,
                    default='', help='Address range to use')
parser.add_argument('--config_file', required=False,
                    default='', help='File with config in to apply')  
parser.add_argument('--remove', required=False, action='store_true',
                    default='', help='If used will remove the config in the specified file by adding "no" to each line of config')                                        

args = parser.parse_args()

conf = args.conf
interface = args.interface
addr = args.addr
config_file = args.config_file
remove = args.remove

if addr:
    network_range = ipaddress.ip_network(addr)
    # from the given IP subnet, build a list of available /32 subnets
    available_addr = list(ipaddress.ip_network(network_range).subnets(prefixlen_diff=(32-network_range.prefixlen)))

# Find the home directory where the .eap.conf file is located
from os.path import expanduser
home = expanduser("~")
hosts = []
n = 1
config_list = []

# read in the contents of the eapi.conf file and build a list of all the hostnames in a list called 'hosts'
with open(home + "/.eapi.conf", "r") as file_object:
    line = file_object.readline()
    while line:
       if "connection" in line:
          hostname = line.lstrip('[connection:')
          hostname = hostname.rstrip(']\n\r')
          hosts.append(hostname)
          line = file_object.readline()
       else:
          line = file_object.readline()

if config_file:
    with open(config_file, 'r') as config_file_object:
        line = config_file_object.readline()
        while line:
            if remove:
               config_list.append("no " + line)
               line = config_file_object.readline()
            else:
               config_list.append(line)
               line = config_file_object.readline()

for x in hosts:    
    switch = pyeapi.connect_to(x)
    if conf:
        command = switch.config(conf)
    elif interface:     
        command = switch.config(["interface " + interface, "ip address " + str(available_addr[n])])
        n += 1
    elif config_file:
        command = switch.config(config_list)





