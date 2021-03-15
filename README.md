# Arista_scripts

Just a bunch of useful python scripts to manage and configure Arista switches. Note all written in python3.x so unlikely to work with python2.x.

## point-to-point-addressing.py

Uses pyeapi so you'll need to install that and setup a .eapi.conf file in your home directory, an example is in the repository here. Simply this script takes a subnet (e.g. 192.168.1.0/24) as an input and then uses that to address all the point to point links in the topology that it discovers using LLDP. Each link is given a /30 from the range.

Run the script using the following:
.\point-to-point-addressing.py {IP-SUBNET}

## bugalertUpdate.py

This script is for situations where your CVP server doesn't have internet access but you have a jump host which can access CVP and has internet connectivity. The script pulls down the latest AlertBase-CVP.json file from arista.com and uploads it to your CVP server and restarts the required processes. It needs as inputs a valid arista.com profile token, the IP address of your CVP server and the root password. These can be hardcoded into the script by editing the 'default' values in the parser lines of code or passed as commmand line options. 

Run the script using the following:
.\bugalertUpdate.py --api {API TOKEN} --cvp {CVP IP ADDRESS} --rootpw {ROOT PASSWORD}

The script can then be scheduled to run daily for example on the jumphost to keep the bug database up to date.

Requires paramiko and scp modules installing

## eos_download.py

This script is for situations where your CVP server doesn't have internet access but you have a jump host which can access CVP and has internet connectivity. The script downloads the specified EOS image locally and then uploads to the CVP server and creates an image bundle with the image in. It needs as inputs a valid arista.com profile token, the IP address of your CVP server and the root password along with the image version (e.g. 4.22.3F) and the WebGUI username and password of the CVP server you'd like to upload it with. These can be hardcoded into the script by editing the 'default' values in the parser lines of code or passed as commmand line options.

The script can also simply be used as a quick way to download images from arista.com without having to login to the website, browse through to find the right image and download through a browser. For this use case only the API token, image version and optional type of image option (for International, 64-bit, vEOS etc. images). CVP releases can also be downloaded by specifying the version of CVP with the --ver argument in the form cvp-2020.1.1 for example and then with the --img argument, whether the ova, kvm, rpm or upgrade variant is required. CVP applications like Remedy, IPAM and CloudBuilder can be downloaded with the --img arguments remedy, ipam or cloudbuilder respectively.

Finally this script can be installed on an Eve-NG server to download an image and then createthe qcow2 image in a folder based on the image version for use in Eve topologies. Just add --eve to the command when run. If ZTP for the vEOS-lab image is not required, the --disable_ztpoption will mount the image and set ZTP to disabled. Note vEOS-lab images are best to use for Eve-NG.

If running the script on a non-shared environment, the user's API key could be hardcoded into the script to save having to use it on the command line. To do this, enter the API key as thedefault value in the argparse section and change the required value to False.

Requires tqdm, paramiko, requests and scp modules installing

## dns_entries.py

This script uses pyeapi, parses all the L3 interfaces on all the switches in the eapi.conf file and creates a hosts file with DNS to IP address mappings in the format 'ip host <HOSTNAME-INTERFACE> <INTERFACE-IP-ADDRESS>' which can then be copied and pasted into EOS devices. Then things like traceroute will be able to show all the hosts in the path for example.

Run the script using the following:
.\dns_entries.py

## run_command.py

Script to apply commands to all switches defined in eapi.conf. Can simply apply a single command, used to create Loopback interfaces on each switch with incrementing IP addresses or can read in a file containing a chunk of config to be applied to all devices. Can also apply config to all Leaf switches (assumes your hostnames contain ‘leaf), all Spine switches (assumes your hostnames contain ‘spine’) or just all switches. When using the config file option, it can also remove all config in the file by simply adding ‘no’ to each command, be aware this is a fairly ‘dumb’ removal of config so it’s not going to work for something like removing a BGP neighbour as it’ll put no in front of ‘router bgp’ so use carefully.

Run the script using the following: ./run_command.py [–conf {CONFIG LINE}] [--interface {INTERFACE} –addr {ADDRESS RANGE}] [--config_file {FILENAME} [--remove]] [--device {‘Leaf’|’Spine’}]

## create_eapi_conf.py

Script to create an eapi.conf file for use with pyeapi given an existing network configured within a block of management IP addresses (script will skip over any IP's it can't connect to). Script will get the hostname from each switch and build the eapi.conf file. Needs the switch username and password input. Assumes https as the transport for each switch.

Run the script using the following: .\create_eapi_conf.py --addr {START IP ADDRESS} –num {NUMBER OF ADDRESSES TO TRY} --user {USERNAME} --passwd {PASSWORD}

## mcast_traffic.py

Script to generate multicast traffic from an EOS switch. Simply copy the script to flash:. The INTERFACE option needs to be in the linux form so Et1 for Ethernet1 for example.

Run the script using the following: .\mcast_traffic.py --interface {INTERFACE} --mcast_group {MULTICAST IP} --number {NUMBER OF PACKETS PER SECOND} --size {PACKET SIZE}

## CVP_configlet_builder_encrypt_passwords.py

A Python script for use within a CVP configlet builder which reads in a static configlet
which contains local usernames and the enable password. This static configlet can be edited 
to update the unencrypted passwords using the config "username <USER> secret <PASSWORD>" 
syntax. Then run the builder configlet which will update the static configlet with the 
SHA512 encrypted versions of the passwords. Therefore the static configlet doesn't contain
clear text passwords and CVP doesn't generate config compliance issues.

INSTALLATION
1. create a configlet builder in CVP
2. paste this script in to the Main Script box, no Form is required.
3. edit the configlet_name variable which contain the name of the static configlet containing
the local usernames and passwords 
4. click on Generate
5. then execute the Tasks which are created assuming the configlet is already applied to some devices
