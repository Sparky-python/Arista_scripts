#!/usr/bin/python3

"""
DESCRIPTION
Script to create an eapi.conf file for use with pyeapi given an existing network configured within a block of management IP addresses (script will skip over any IP's it can't connect to). Script will get the hostname from each switch and build the eapi.conf file. Needs the switch username and password input. Assumes https as the transport for each switch.

Run the script using the following:
.\create_eapi_conf.py --addr 192.168.1.1 --num 20 --user cvpadmin --passwd arista123

This example will try to connect to all IP's from 192.168.1.1 to 192.168.1.20

"""
__author__ = 'marayson'

import argparse
import ssl
import socket, struct
from jsonrpclib import Server

try:
  _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
# Legacy Python that doesn't verify HTTPS certificates by default
  pass
else:
# Handle target environment that doesn't support HTTPS verification
  ssl._create_default_https_context = _create_unverified_https_context


parser = argparse.ArgumentParser()
parser.add_argument('--addr', required=True,
                    default='', help='First management IP address in range')
parser.add_argument('--num', required=True,
                    default='', help='Number of addresses to try from first IP address')  
parser.add_argument('--user', required=True,
                    default='', help='Username to access the switches')
parser.add_argument('--passwd', required=True,
                    default='', help='Password to access the switches')  


args = parser.parse_args()

addr = args.addr
num = args.num
user = args.user
passwd = args.passwd

def ip2long(ip):
    """
    Convert an IP string to long
    """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]
    
def long2ip(long):
    """
    Convert a long to an IP string
    """
    stringIP = socket.inet_ntoa(struct.pack('!L', long))
    return stringIP

def getNextIPAddress(ip):
    """
    Returns the next IP address
    """
    ip_address_long = ip2long(ip) + 1
    ip = long2ip(ip_address_long)
    return ip

# Find the home directory where the .eap.conf file is located
from os.path import expanduser
home = expanduser("~")
hosts = []
n = 1
config_list = []
socket.setdefaulttimeout(3)

file_object = open(home + "/.eapi.conf", 'x')

current_ip = addr

for i in range(int(num)):
    api_url = "https://" + user + ":" + passwd + "@" + current_ip + "/command-api"
    switch = Server(api_url)
    try:
        response = switch.runCmds(1, ["show hostname"])
        hostname = response[0]["hostname"]
        file_object.write("[connection:" + hostname + "]\n")
        file_object.write("host: " + current_ip + "\n")
        file_object.write("username: " + user + "\n")
        file_object.write("password: " + passwd + "\n")
        file_object.write("transport: https\n")
        file_object.write("\n")
    except socket.error as ERR:
        print("Can't connect to " + current_ip)
    current_ip = getNextIPAddress(current_ip)

file_object.close
