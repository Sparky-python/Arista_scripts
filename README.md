# Arista_scripts

Just a bunch of useful python scripts to manage and configure Arista switches. Note all written in python3.x so unlikely to work with python2.x.

## point-to-point-addressing.py

Uses pyeapi so you'll need to install that and setup a .eapi.conf file in your home directory, an example is in the repository here. Simply this script takes a subnet (e.g. 192.168.1.0/24) as an input and then uses that to address all the point to point links in the topology that it discovers using LLDP. Each link is given a /30 from the range.

Run the script using the following:
.\point-to-point-addressing.py <IP-SUBNET>

## bugalertUpdate.py

This script is for situations where your CVP server doesn't have internet access but you have a jump host which can access CVP and has internet connectivity. The script pulls down the latest AlertBase-CVP.json file from arista.com and uploads it to your CVP server and restarts the required processes. It needs as inputs a valid arista.com profile token, the IP address of your CVP server and the root password. These can be hardcoded into the script by editing the 'default' values in the parser lines of code or passed as commmand line options. 

Run the script using the following:
.\bugalertUpdate.py --api {API TOKEN} --cvp {CVP IP ADDRESS} --rootpw {ROOT PASSWORD}

The script can then be scheduled to run daily for example on the jumphost to keep the bug database up to date.

Requires paramiko and scp modules installing

## eos_download.py

This script is for situations where your CVP server doesn't have internet access but you have a jump host which can access CVP and has internet connectivity. The script downloads the specified EOS image locally and then uploads to the CVP server and creates an image bundle with the image in. It needs as inputs a valid arista.com profile token, the IP address of your CVP server and the root password along with the image version (e.g. 4.22.3F) and the WebGUI username and password of the CVP server you'd like to upload it with. These can be hardcoded into the script by editing the 'default' values in the parser lines of code or passed as commmand line options. 

The script can also simply be used as a quick way to download images from arista.com without having to login to the website with SSO, browse through to find the right image and download through a browser. For this use case only the API token, image version and optional international flag options are used (--i)

Run the script using the following:
.\eos_download.py --api {API TOKEN} --file {EOS VERSION} [--file {TERMINATTR VERSION}] [--cvp {CVP IP ADDRESS} --rootpw {ROOT PASSWORD} --cvp_user {GUI CVP USERNAME} --cvp_passwd {GUI CVP PASSWORD}]

Requires tqdm, paramiko and scp modules installing