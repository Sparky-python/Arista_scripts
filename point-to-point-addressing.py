#!/usr/bin/python3

import pyeapi
import re
import ssl
import sys
import ipaddress
import pprint

try:
  _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
# Legacy Python that doesn't verify HTTPS certificates by default
  pass
else:
# Handle target environment that doesn't support HTTPS verification
  ssl._create_default_https_context = _create_unverified_https_context

network_range = ipaddress.ip_network(sys.argv[1])
# ip_list = open("IP-Address-List.txt", "r")
hosts = []

# Find the home directory where the .eap.conf file is located
from os.path import expanduser
home = expanduser("~")

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

# create empty dictionary called 'topology'
topology = {}
z = 1
# go through the hosts list, run the 'show lldp neighbors' command and populate the topology dictionary with the info
for x in hosts:
    switch = pyeapi.connect_to(x)
    lldp = switch.enable("show lldp neighbors")
    links = []
    for i in lldp[0]["result"]["lldpNeighbors"]:
        links.append({'local_int': i["port"] , 'neighbor_sw': (i["neighborDevice"].rsplit(".")[0]) , 'neighbor_int': i["neighborPort"] , 'ip_address': ""})
    topology[x] =links

n = 0

# from the given IP subnet, build a list of available /30 subnets
available_subnets = list(ipaddress.ip_network(network_range).subnets(prefixlen_diff=(30-network_range.prefixlen)))

# go through each host in the topology dictionary
for host in topology:
    switch = pyeapi.connect_to(host)
    r = 0
# for each interface for the host which has LLDP neighbors
    for interface in topology[host]:
# if the interface IP addresss hasn't been populated yet
        if interface["ip_address"] == '':
            switch = pyeapi.connect_to(host)
# configure the interface on the current host with the next available IP 
            switch.config(['interface ' + interface["local_int"], 'no switchport', 'ip pim sparse-mode', 'ip address ' + str(list(available_subnets[n].hosts())[0]) + '/30'])
            topology[host][r]["ip_address"] = str(list(available_subnets[n].hosts())[0])
            s = 0
            for neighbor_int in topology[(topology[host][r]["neighbor_sw"])]:
                if neighbor_int["local_int"] == topology[host][r]["neighbor_int"]:
                    switch = pyeapi.connect_to((topology[host][r]["neighbor_sw"]))
                    switch.config(['interface ' + neighbor_int["local_int"], 'no switchport', 'ip address ' + str(list(available_subnets[n].hosts())[1]) + '/30'])
                    topology[(topology[host][r]["neighbor_sw"])][s]["ip_address"] = str(list(available_subnets[n].hosts())[1])
                    break
                s += 1
            n += 1
            r +=1
        else:
            r += 1



