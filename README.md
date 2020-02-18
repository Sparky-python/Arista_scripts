# Arista_scripts

Just a bunch of useful python scripts to manage and configure Arista switches.

## point-to-point-addressing.py

Uses pyeapi so you'll need to install that and setup a .eapi.conf file in your home directory, an example is in the repository here. Simply this script takes a subnet (e.g. 192.168.1.0/24) as an input and then uses that to address all the point to point links in the topology that it discovers using LLDP. Each link is given a /30 from the range.

## bugalertUpdate.py

This script is for situations where your CVP server doesn't have internet access but you have a jump host which can access CVP and has internet connectivity. The script pulls down the latest AlertBase-CVP.json file from arista.com and uploads it to your CVP server and restarts the required processes. It needs as inputs a valid arista.com profile token, the IP address of your CVP server and the root password. These can be hardcoded into the script by editing the 'default' values in the parser lines of code or passed as commmand line options. 

Run the script using the following:
.\bugalertUpdate.py --api {API TOKEN} --cvp {CVP IP ADDRESS} --rootpw {ROOT PASSWORD}

The script can then be scheduled to run daily for example on the jumphost to keep the bug database up to date.