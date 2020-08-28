#!/usr/bin/python

import time,sys,os,subprocess
import re
import socket

interface = raw_input("Please enter the interface you'd like to send multicast traffic out of in the format et5 for example: ")
mcast_group = raw_input("Please enter the multicast group you'd like to send traffic to: ")
number = raw_input("Please enter the number of packets per second you'd like to send: ")
size = raw_input("Please enter the packet size you'd like to use: ")

output = subprocess.Popen(['ifconfig', interface], stdout = subprocess.PIPE, stderr=subprocess.STDOUT)
stdout,stderr = output.communicate()
ether_pos = stdout.find("ether")
ip_pos = stdout.find("inet")
netmask_pos = stdout.find("netmask")
src_mac = stdout[ether_pos+6:ether_pos+23]
src_ip = stdout[ip_pos+5:netmask_pos-2]


def convert_multicast_ip_to_mac(ip_address):
    """Convert the Multicast IP to it's equivalent Multicast MAC.
    Source info: https://technet.microsoft.com/en-us/library/cc957928.aspx
    """
    # Convert the IP String to a bit sequence string
    try:
        ip_binary = socket.inet_pton(socket.AF_INET, ip_address)
        ip_bit_string = ''.join(['{0:08b}'.format(ord(x)) for x in ip_binary])
    except socket.error:
        raise RuntimeError('Invalid IP Address to convert.')

    # The low order 23 bits of the IP multicast address are mapped directly to the low order
    # 23 bits in the MAC-layer multicast address
    lower_order_23 = ip_bit_string[-23:]

    # The high order 25 bits of the 48-bit MAC address are fixed
    high_order_25 = '0000000100000000010111100'

    mac_bit_string = high_order_25 + lower_order_23

    # Convert the bit string to the Typical MAC Address String
    final_string = '{0:012X}'.format(int(mac_bit_string, 2))
    mac_string = ':'.join(s.encode('hex') for s in final_string.decode('hex'))
    return mac_string.upper()


mcast_mac = convert_multicast_ip_to_mac(mcast_group)

while True:
   try:
      os.system("sudo ethxmit -S " + src_mac + " -D " + mcast_mac + " --ip-src=" + src_ip + " --ip-dst=" + mcast_group + " -n " + number + " -s " + size + " " + interface)
      time.sleep(1)
   except KeyboardInterrupt:
      raise
