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

The script can also simply be used as a quick way to download images from arista.com without having to login to the website with SSO, browse through to find the right image and download through a browser. For this use case only the API token and image version are used. For virtual EOS images, use the --virt option, specifying vEOS, vEOS-lab or cEOS. Otherwise the standard image for a hardware switch is downloaded.

This script can also be used on an Eve-NG server to add EOS images ready for use in a topology. Use the --virt option to specify vEOS or vEOS-lab and add '--eve True' at the end of the arguments. This will download the image, covert to a qcow2 format, move to a folder named based on the image ready to choose in the GUI and finally delete the downloaded image.

Run the script using the following:
.\eos_download.py --api {API TOKEN} --ver {EOS VERSION} [--ver {TERMINATTR VERSION}] [--img {INT|64|2GB|2GB-INT|vEOS|vEOS-lab|vEOS64-lab|cEOS|cEOS64|source} --cvp {CVP IP ADDRESS} --rootpw {ROOT PASSWORD} --cvp_user 
{GUI CVP USERNAME} --cvp_passwd {GUI CVP PASSWORD} --eve]

Requires tqdm, paramiko, requests and scp modules installing

## dns_entries.py

This script uses pyeapi, parses all the L3 interfaces on all the switches in the eapi.conf file and creates a hosts file with DNS to IP address mappings in the format 'ip host <HOSTNAME-INTERFACE> <INTERFACE-IP-ADDRESS>' which can then be copied and pasted into EOS devices. Then things like traceroute will be able to show all the hosts in the path for example.

Run the script using the following:
.\dns_entries.py

## run_command.py

Script to apply commands to all switches defined in eapi.conf. Can simply apply a single command using --conf, used to create Loopback interfaces with incrementing IP address using --interface and --addr or can read in a file containing a chunk of config to be applied to all devices using --config_file.