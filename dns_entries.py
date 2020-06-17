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


# Find the home directory where the .eap.conf file is located
from os.path import expanduser
home = expanduser("~")
hosts = []
n = 1
hosts_file = open("hosts", 'a+')

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
for x in hosts:
    switch = pyeapi.connect_to(x)
    command = switch.enable("show ip interface brief")
    for key in command[0]['result']['interfaces'].keys():
        hosts_file.write("ip host " + x + "-" + key + " " + command[0]['result']['interfaces'][key]['interfaceAddress']['ipAddr']['address'] + "\n")
hosts_file.close()

