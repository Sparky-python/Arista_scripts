#!/usr/bin/env python3
#
# Copyright (c) 2021, Arista Networks, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#  - Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#  - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#  - Neither the name of Arista Networks nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARISTA NETWORKS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# eos_download.py
#
#    Written by:
#       Mark Rayson, Arista Networks
#
"""
DESCRIPTION
This script is for situations where your CVP server doesn't have internet access but you 
have a jump host which can access CVP and has internet connectivity. The script downloads 
the specified EOS image locally and then uploads to the CVP server and creates an image 
bundle with the image in. It needs as inputs a valid arista.com profile token, the IP 
address of your CVP server and the root password along with the image version 
(e.g. 4.22.3F) and the WebGUI username and password of the CVP server you'd like to upload 
it with. These can be hardcoded into the script by editing the 'default' values in the 
parser lines of code or passed as commmand line options.

The script can also simply be used as a quick way to download images from arista.com 
without having to login to the website, browse through to find the right image and download 
through a browser. For this use case only the API token, image version and optional type of 
image option (for International, 64-bit, vEOS etc. images). CVP releases can also be 
downloaded by specifying the version of CVP with the --ver argument in the form cvp-2020.1.1 
for example and then with the --img argument, whether the ova, kvm, rpm or upgrade variant is 
required. CVP applications like Remedy, IPAM and CloudBuilder can be downloaded with the --img 
arguments remedy, ipam or cloudbuilder respectively.

Finally this script can be installed on an Eve-NG server to download an image and then create
the qcow2 image in a folder based on the image version for use in Eve topologies. Just add 
--eve to the command when run. If ZTP for the vEOS-lab image is not required, the --disable_ztp
option will mount the image and set ZTP to disabled. Note vEOS-lab images are best to use for 
Eve-NG.

If running the script on a non-shared environment, the user's API key could be hardcoded into
the script to save having to use it on the command line. To do this, enter the API key as the
default value in the argparse section and change the required value to False.


INSTALLATION
1. python3 needs to be installed on the host
2. pip3 install scp paramiko tqdm requests
3. wget https://github.com/Sparky-python/Arista_scripts/blob/master/eos_download.py
4. Run the script using the following: .\eos_download.py --api {API TOKEN} --ver 
{EOS VERSION|TERMINATTR VERSION|CVP VERSION} [--ver {EOS VERSION|TERMINATTR VERSION|CVP VERSION}] [--img {INT|64|2GB|2GB-INT|vEOS|vEOS-lab|vEOS64-lab|cEOS|cEOS64|source|ova|kvm|rpm|upgrade|ipam|remedy|cloudbuilder} --cvp {CVP IP ADDRESS} --rootpw {ROOT PASSWORD} --cvp_user 
{GUI CVP USERNAME} --cvp_passwd {GUI CVP PASSWORD} --eve --overwrite --disable_ztp] 


"""
__author__ = 'marayson'

import base64
import xml.etree.ElementTree as ET
import sys
import requests
import argparse
import json
import warnings
import urllib.request
from tqdm import tqdm
from paramiko import SSHClient
from scp import SCPClient
import paramiko
import os
import os.path
import re
import time
import hashlib

# part of progress bar code
def viewBar(a,b):
    # original version
    res = a/int(b)*100
    sys.stdout.write('\rComplete precent: %.2f %%' % (res))
    sys.stdout.flush()

# part of progress bar code
def tqdmWrapViewBar(*args, **kwargs):
    try:
        from tqdm import tqdm
    except ImportError:
        # tqdm not installed - construct and return dummy/basic versions
        class Foo():
            @classmethod
            def close(*c):
                pass
        return viewBar, Foo
    else:
        pbar = tqdm(*args, **kwargs)  # make a progressbar
        last = [0]  # last known iteration, start at 0
        def viewBar2(a, b):
            pbar.total = int(b)
            pbar.update(int(a - last[0]))  # update pbar with increment
            last[0] = a  # update last known iteration
        return viewBar2, pbar  # return callback, tqdmInstance

# function to download a file and display progress bar using tqdm        
def download_file(url, filename):
   """
   Helper method handling downloading large files from `url` to `filename`. Returns a pointer to `filename`.
   """
   chunkSize = 1024
   r = requests.get(url, stream=True)
   with open(filename, 'wb') as f:
      pbar = tqdm( unit="B", total=int( r.headers['Content-Length'] ), unit_scale=True, unit_divisor=1024 )
      for chunk in r.iter_content(chunk_size=chunkSize): 
         if chunk: # filter out keep-alive new chunks
            pbar.update (len(chunk))
            f.write(chunk)
   return filename

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# use argparse to take the user input, can fill in default values here if the user wishes
# especially useful for the API key which won't change for a particular user
warnings.filterwarnings("ignore")
parser = argparse.ArgumentParser()
parser.add_argument('--api', required=True,
                    default='', help='arista.com user API key')
parser.add_argument('--ver', required=True, action='append',
                    default=[], help='EOS and swix iamges to download, repeat --ver option for each file. EOS images should be in the form 4.22.1F, cvp-2020.1.1 for CVP and TerminAttr-1.7.4 for TerminAttr files')
parser.add_argument('--img', required=False,
                    default='', help='Type of EOS image required, INT, 64 (64-bit), 2GB (for 2GB flash platforms), 2GB-INT, vEOS, vEOS-lab, vEOS64-lab, cEOS, cEOS64, RN (to download the Release Notes) or source (to download the source files). If none specified assumes normal EOS image for switches. For CVP, specify kvm, ova, rpm or upgrade for the img flag. For CVP Applications, specify remedy, ipam or cloudbuilder')
parser.add_argument('--cvp', required=False,
                    default='', help='IP address of CVP server')
parser.add_argument('--rootpw', required=False,
                    default='', help='Root password of CVP server')
parser.add_argument('--cvp_user', required=False,
                    default='', help='CVP WebUI Username')
parser.add_argument('--cvp_passwd', required=False,
                    default='', help='CVP WebUI Password')
parser.add_argument('--eve', required=False, action='store_true',
                    help="Use this option if you're running this on Eve-NG to create a qcow2 image")
parser.add_argument('--overwrite', required=False, action='store_true',
                    help="Use this option if you would like to overwrite any previously downloaded files")
parser.add_argument('--disable_ztp', required=False, action='store_true',
                    help='Disable ZTP mode for vEOS-lab images running in Eve-NG')

args = parser.parse_args()

api = args.api
file_list = args.ver # this will be a list of the files requested to be downloaded
img = args.img
cvp = args.cvp
rootpw = args.rootpw
cvp_user = args.cvp_user
cvp_passwd = args.cvp_passwd
eve = args.eve
overwrite = args.overwrite
ztp = args.disable_ztp

# the api key needs converting into base64 which outputs a byte value and then decoding to a string
creds = (base64.b64encode(api.encode())).decode("utf-8")

# there are 3 steps to downloading an image via the API, first is to get a session code
session_code_url = "https://www.arista.com/custom_data/api/cvp/getSessionCode/"
jsonpost = {'accessToken': creds}
result = requests.post(session_code_url, data=json.dumps(jsonpost))
if result.json()["status"]["message"] == 'Access token expired':
   print("The API token has expired. Please visit arista.com, click on your profile and select Regenerate Token then re-run the script with the new token.")
   sys.exit()
elif result.json()["status"]["message"] == 'Invalid access token':
   print("The API token is incorrect. Please visit arista.com, click on your profile and check the Access Token. Then re-run the script with the correct token.")
   sys.exit()
session_code = (result.json()["data"]["session_code"])

# then get the current folder tree, similar to what you see on the download page in XML format
folder_tree_url = "https://www.arista.com/custom_data/api/cvp/getFolderTree/"
jsonpost = {'sessionCode': session_code}
result = requests.post(folder_tree_url, data=json.dumps(jsonpost))
folder_tree = (result.json()["data"]["xml"])

root = ET.fromstring(folder_tree)
path = ""

# for each image the user wishes to download
for image in file_list:
   if 'INT' in img: # if the user wants the international/federal variant
      z = 1 # corresponds to "EOS International / Federal" top level folder
      if img == 'INT':
         eos_filename = "EOS-" + image + "-INT.swi" # filename should be something like EOS-4.22.1F-INT.swi
         image = image.rstrip("-INT") # image should be 4.22.1F, need to remove the -INT
      elif img == '2GB-INT':
         eos_filename = "EOS-2GB-" + image + "-INT.swi" # filename should be something like EOS-4.22.1F-INT.swi
         image = image.rstrip("-INT") # image should be 4.22.1F, need to remove the -INT
   elif "TerminAttr" in image: # if the user wants a TerminAttr image
      z = 3 # corresponds to "CloudVision" top level folder
      eos_filename = image + "-1.swix" # filename should be something like TerminAttr-1.7.4-1.swix
   elif "ipam" in img: # if the user wants a CVP IPAM image
      z = 2 # corresponds to "CloudVision" top level folder
      eos_filename = "cvp-ipam-backend-v" + image + "-1.x86_64.rpm" # filename should be something like cvp-ipam-backend-v1.2.1-1.x86_64.rpm
      ipam_filename = "ipam-ui-v" + image + "-1.noarch.rpm" # 2 files are needed for CVP IPAM
   elif "remedy" in img: # if the user wants a CVP Remedy image
      z = 2 # corresponds to "CloudVision" top level folder
      eos_filename = "remedy_cvp-" + image + "-1.noarch.rpm" # filename should be something like remedy_cvp-1.0.0-1.noarch.rpm
   elif "cloudbuilder" in img: # if the user wants a CVP CloudBuilder image
      z = 2 # corresponds to "CloudVision" top level folder
      eos_filename = "cloud-builder-v" + image + "-1.x86_64.rpm" # filename should be something like cloud-builder-v2.4.0-1.x86_64.rpm
      cb_filename = "cloud-builder-frontend-v" + image + "-1.noarch.rpm" # 2 files are needed for CVP CloudBuilder
   elif "cvp" in image: # if the user wants a CVP image
      z = 2 # corresponds to "CloudVision" top level folder
      if img == 'ova':
         eos_filename = image + ".ova"
      elif img == 'kvm':
         eos_filename = image + "-kvm.tgz"
      elif img == 'rpm':
         eos_filename = image[:4] + "rpm-installer-" + image[4:]
      elif img == 'upgrade':
         eos_filename = image[:4] + "upgrade-" + image[4:] + ".tgz"
   else: # otherwise it's a normal EOS image they're after
      z = 0 # corresponds to "EOS" top level folder
      if img == 'cEOS':
         eos_filename = "cEOS-lab-" + image + ".tar.xz"
      elif img == 'cEOS64':
         eos_filename = "cEOS64-lab-" + image + ".tar.xz"
      elif img == 'vEOS':
         eos_filename = "vEOS-" + image + ".vmdk"
      elif img == 'vEOS-lab':
         eos_filename = "vEOS-lab-" + image + ".vmdk"
      elif img == 'vEOS64-lab':
         eos_filename = "vEOS64-lab-" + image + ".vmdk"
      elif img == '2GB':
         eos_filename = "EOS-2GB-" + image + ".swi"
      elif img == '64':
         eos_filename = "EOS64-" + image + ".swi"
      elif img == 'RN':
         eos_filename = "RN-" + image + "-"
      elif img == 'source':
         eos_filename = "EOS-" + image + "-source.tar"
      else:
         eos_filename = "EOS-" + image + ".swi" # filename should be something like EOS-4.22.1F.swi


   if os.path.isfile(eos_filename) and not overwrite: # check if the image exists in the current directory, if so no need to download again
      print ("\nLocal copy of file already exists")
   else:
      for child in root[z].iter('dir'):
         #print(child.attrib)
         if child.attrib == {'label': "EOS-" + image}:
            for grandchild in child.iter('file'):
               #print(grandchild.text)
               if grandchild.text == (eos_filename):
                  path = grandchild.attrib['path'] # corresponds to the download path
               elif grandchild.text == (eos_filename + '.sha512sum'):
                  sha512_path = grandchild.attrib['path'] # corresponds to the download path of the sha512 checksum
               elif ('RN' in grandchild.text) and (eos_filename in grandchild.text):
                  eos_filename = grandchild.text
                  path = grandchild.attrib['path'] # corresponds to the download path
         elif child.attrib == {'label': image} or child.attrib == {'label': image + "-1"}  : # special case for TerminAttr as some releases have -1 in the folder name others don't but the filename always has the -1
            #print (child.attrib)
            for grandchild in child.iter('file'):
               if grandchild.text == (eos_filename):
                  path = grandchild.attrib['path']
               elif grandchild.text == (eos_filename + '.md5sum'):
                  sha512_path = grandchild.attrib['path'] # corresponds to the download path of the MD5 checksum
         elif child.attrib == {'label': image[4:]} : # special case for CVP as labels are in the format 2020.1.1 so we need to remove 'cvp-' to match
            #print (child.attrib)
            for grandchild in child.iter('file'):
               if grandchild.text == (eos_filename):
                  path = grandchild.attrib['path']
               elif grandchild.text == (eos_filename + '.md5'):
                  sha512_path = grandchild.attrib['path'] # corresponds to the download path of the MD5 checksum
         elif child.attrib == {'label': "CVP IPAM Application"} and img == "ipam":
            for grandchild in child.iter('file'):
               #print(grandchild.text)
               if grandchild.text == (eos_filename):
                  path = grandchild.attrib['path']
               elif grandchild.text == (ipam_filename):
                  path2 = grandchild.attrib['path']
               elif grandchild.text == (eos_filename + '.sha512sum'):
                  sha512_path = grandchild.attrib['path'] # corresponds to the download path of the SHA512 checksum
               elif grandchild.text == (ipam_filename + '.sha512sum'):
                  sha512_path2 = grandchild.attrib['path'] # corresponds to the download path of the SHA512 checksum
         elif child.attrib == {'label': "Remedy-CVP"} and img == "remedy":
            for grandchild in child.iter('file'):
               #print(grandchild.text)
               if grandchild.text == (eos_filename):
                  path = grandchild.attrib['path']
               elif grandchild.text == (eos_filename + '.sha512sum'):
                  sha512_path = grandchild.attrib['path'] # corresponds to the download path of the SHA512 checksum
         elif child.attrib == {'label': "Cloud Builder"} and img == "cloudbuilder":
            for grandchild in child.iter('file'):
               #print(grandchild.text)
               if grandchild.text == (eos_filename):
                  path = grandchild.attrib['path']
               elif grandchild.text == (cb_filename):
                  path2 = grandchild.attrib['path']
               elif grandchild.text == (eos_filename + '.sha512sum'):
                  sha512_path = grandchild.attrib['path'] # corresponds to the download path of the SHA512 checksum
               elif grandchild.text == (cb_filename + '.sha512sum'):
                  sha512_path2 = grandchild.attrib['path'] # corresponds to the download path of the SHA512 checksum


      if path == "": # this means we haven't found the image so we exit the script at this point
         print("\nFile " + eos_filename +" does not exist.")
         sys.exit()
      # the 3rd part of downloading a file is to use the path and session code to get the actual direct download link URL
      download_link_url = "https://www.arista.com/custom_data/api/cvp/getDownloadLink/"
      jsonpost = {'sessionCode': session_code, 'filePath': path}
      result = requests.post(download_link_url, data=json.dumps(jsonpost))
      download_link = (result.json()["data"]["url"])         


      print(eos_filename + " is currently downloading....")
      # download the file to the current folder
      download_file (download_link, eos_filename)
      if img == "ipam":  # for CVP IPAM there's 2 files to download so this grabs the 2nd file
         jsonpost = {'sessionCode': session_code, 'filePath': path2}
         result = requests.post(download_link_url, data=json.dumps(jsonpost))
         download_link = (result.json()["data"]["url"])
         print(ipam_filename + " is currently downloading....")  
         download_file(download_link, ipam_filename)
      elif img == "cloudbuilder":  # for CVP CloudBuilder there's 2 files to download so this grabs the 2nd file
         jsonpost = {'sessionCode': session_code, 'filePath': path2}
         result = requests.post(download_link_url, data=json.dumps(jsonpost))
         download_link = (result.json()["data"]["url"])
         print(cb_filename + " is currently downloading....")  
         download_file(download_link, cb_filename)


      if (img != 'source') and (img != 'RN'):
         jsonpost = {'sessionCode': session_code, 'filePath': sha512_path}
         sha512_result = requests.post(download_link_url, data=json.dumps(jsonpost))
         sha512_download_link = (sha512_result.json()["data"]["url"])
         if "TerminAttr" in image:
            download_file (sha512_download_link, eos_filename + '.md5sum')
         if "cvp" in image:
            download_file (sha512_download_link, eos_filename + '.md5')
         else:
            download_file (sha512_download_link, eos_filename + '.sha512sum')
         for line in urllib.request.urlopen(sha512_download_link):
            sha512_file = line

         if img == "ipam":
            jsonpost = {'sessionCode': session_code, 'filePath': sha512_path2}
            sha512_result = requests.post(download_link_url, data=json.dumps(jsonpost))
            sha512_download_link = (sha512_result.json()["data"]["url"])
            download_file (sha512_download_link, ipam_filename + '.sha512sum')
            for line in urllib.request.urlopen(sha512_download_link):
               sha512_file2 = line
      
         if img == "cloudbuilder":
            jsonpost = {'sessionCode': session_code, 'filePath': sha512_path2}
            sha512_result = requests.post(download_link_url, data=json.dumps(jsonpost))
            sha512_download_link = (sha512_result.json()["data"]["url"])
            download_file (sha512_download_link, cb_filename + '.sha512sum')
            for line in urllib.request.urlopen(sha512_download_link):
               sha512_file2 = line

         if "TerminAttr" in image:
            download_file_chksum = md5(eos_filename)  # calculate the MD5 checksum of the downloaded file, note only MD5 checksum available for TerminAttr images
            if (download_file_chksum == (sha512_file.decode("utf-8").split(" ")[0])):
               print ("\nMD5 checksum correct")
            else:
               print ("\nMD5 checksum incorrect, downloaded file must be corrupt.")
               sys.exit()
         elif "cvp" in image:
            download_file_chksum = md5(eos_filename)  # calculate the MD5 checksum of the downloaded file, note only MD5 checksum available for CVP images
            if (download_file_chksum == sha512_file.decode("utf-8").rstrip('\n')):
               print ("\nMD5 checksum correct")
            else:
               print ("\nMD5 checksum incorrect, downloaded file must be corrupt.")
               sys.exit()
         else:
            download_file_chksum = os.popen("openssl sha512 " + eos_filename).read()  # calculate the SHA512 checksum of the downloaded file
            if (download_file_chksum.split(" ")[1].rstrip('\n')) == (sha512_file.decode("utf-8").split(" ")[0]):
               print ("\nSHA512 checksum correct")
            else:
               print ("\nSHA512 checksum incorrect, downloaded file must be corrupt.")
               sys.exit()

if cvp != '': # if the CVP IP address has been specified when running the script, the user must want to upload the image to CVP
   if (rootpw == '') or (cvp_user == '') or (cvp_passwd == ''):
      print ("\nTo upload images to CVP, the root password, GUI username and password all need to be specified. Please re-run the script with the --rootpw, --cvp_user and --cvp_passwd options")
      sys.exit()
   terminattr_filename = ""
   t = paramiko.Transport((cvp, 22))
   t.connect(username="root", password=rootpw)
   sftp = paramiko.SFTPClient.from_transport(t)
   for image in file_list:
      if "-INT" in image:
         z = 1
         filename = "EOS-" + image + ".swi"
         image = image.rstrip("-INT")
         eos_filename = filename
         eos_bundle = image
      elif "TerminAttr" in image:
         z = 3
         filename = image + "-1.swix"
         terminattr_filename = filename
      else:
         z = 0
         filename = "EOS-" + image + ".swi"
         eos_filename = filename
         eos_bundle = image

      print ("\nUploading " + filename + " to CVP")
      cbk, pbar = tqdmWrapViewBar(ascii=True, unit="B", unit_scale=True)
      sftp.put(filename, '/root/' + filename, callback=cbk)
      pbar.close()

   ssh = SSHClient()
   ssh.load_system_host_keys()
   ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   ssh.connect(cvp, username="root", password=rootpw)

   print ("\nFile copied to CVP server\nNow importing " + eos_filename + " into HDBase.")

   if (eos_filename != '') and (terminattr_filename != ''):
      stdin, stdout, stderr = ssh.exec_command('python /cvpi/tools/imageUpload.py --swi ' + eos_filename + ' --swix' + terminattr_filename + ' --bundle EOS-' + eos_bundle + ' --user ' + cvp_user + ' --password ' + cvp_passwd)
   else:
      stdin, stdout, stderr = ssh.exec_command('python /cvpi/tools/imageUpload.py --swi ' + eos_filename + ' --bundle EOS-' + eos_bundle + ' --user ' + cvp_user + ' --password ' + cvp_passwd)
   exit_status = stdout.channel.recv_exit_status()
   if exit_status == 0:
      print ("\nUpload complete")
   else:
      print ("\nFile not uploaded because ")
      if (stdout.read()).decode("utf-8") == "Connecting to CVP\nImage " + eos_filename + " already exists. Aborting.\n":
         print ("Image already exists in CVP")
      elif "SWI does not contain a supported TerminAttr version" in (stderr.read()).decode("UTF-8"):
         print ("SWI does not contain a supported TerminAttr version.")
      else:
         print ("Some other error")
   if ssh:
      ssh.close()

if eve:
   print ("Creating qcow2 image")
   os.system("/opt/qemu/bin/qemu-img convert -f vmdk -O qcow2 " + eos_filename + " hda.qcow2")
   eos_folder_name = ""
   x = eos_filename.split("-")
   for y in x[:-1]:
      eos_folder_name+=str(y.lower())
      eos_folder_name+="-"
   eos_folder_name+=str(x[-1])

   os.system("mkdir -p /opt/unetlab/addons/qemu/" + eos_folder_name.rstrip(".vmdk"))
   os.system("mv hda.qcow2 /opt/unetlab/addons/qemu/" + eos_folder_name.rstrip(".vmdk"))
   os.system("/opt/unetlab/wrappers/unl_wrapper -a fixpermissions")
   os.system("rm "+ eos_filename)
   print ("Image successfully created")

   eve_path = "/opt/unetlab/addons/qemu/" + eos_folder_name.rstrip(".vmdk")
   if ztp:
      print("Mounting volume to disable ZTP")
      os.system("rm -rf " + eve_path + "/raw")
      os.system("mkdir -p " + eve_path + "/raw")
      os.system("guestmount -a {}/hda.qcow2 -m /dev/sda2 {}/raw/".format(eve_path,eve_path))
      with open(eve_path + '/raw/zerotouch-config', 'w') as zfile:
            zfile.write('DISABLE=True')
      print("Unmounting volume at: " + str(eve_path))
      os.system("guestunmount " + eve_path + '/raw/')
      os.system('rm -rf ' + eve_path + '/raw')
      print("Volume has been successfully unmounted at: " + str(eve_path))
