#!/usr/bin/env python3
#
# Copyright (c) 2017, Arista Networks, Inc.
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
# bugalertUpdate.py
#
#    Written by:
#       Mark Rayson, Arista Networks
#
"""
DESCRIPTION
A Python script for updating the AlertBase.json file on CVP when the CVP cannot access 
the internet directly but a jump host is available which can access the internet and CVP.
Script can be run manually, or using a scheduler to automatically check www.arista.com
for database updates for the CVP Bugalerts feature. A local copy of the AlertBase-CVP.json
file will be left in the directory with the script, it is recommended to leave this file in
place as the script will compare this local copy to the latest downloaded one and if they are
the same then no further action will be taken.
To learn more about BugAlerts see: https://eos.arista.com/eos-4-17-0f/bug-alerts/
INSTALLATION
1. python3 needs to be installed on the jump host
2. wget https://github.com/coreyhines/Arista/raw/master/bugalertUpdate.py
3. run the script with.. ./bugalertUpdate.py --api <BUGALERTS TOKEN FROM ARISTA.COM> --cvp <CVP SERVER IP ADDRESS> 
--rootpw <ROOT PASSWORD OF CVP SERVER>
4. python pip install scp, paramiko

Credit to Corey Hinds for original script which this was based on to update BugAlerts file 
in CVX
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

#from datetime import datetime

warnings.filterwarnings("ignore")
parser = argparse.ArgumentParser()
parser.add_argument('--api', required=True,
                    default='2beb105836a4c44b942eed4666d0cd48', help='arista.com user API key')
parser.add_argument('--cvp', required=False,
                    default='', help='IP address of CVP server')
parser.add_argument('--rootpw', required=False,
                    default='', help='Root password of CVP server')
parser.add_argument('--cvp_user', required=False,
                    default='', help='CVP WebUI Username')
parser.add_argument('--cvp_passwd', required=False,
                    default='', help='CVP WebUI Password')
parser.add_argument('--eos', required=True,
                    default='', help='EOS iamge to download')
parser.add_argument('--i', required=False, action='store_true',
                    default=False, help='EOS International/Federal Releases')

args = parser.parse_args()

api = args.api
cvp = args.cvp
rootpw = args.rootpw
cvp_user = args.cvp_user
cvp_passwd = args.cvp_passwd
eos = args.eos
i = args.i

creds = (base64.b64encode(api.encode())).decode("utf-8")

session_code_url = "https://www.arista.com/custom_data/api/cvp/getSessionCode/"
jsonpost = {'accessToken': creds}
result = requests.post(session_code_url, data=json.dumps(jsonpost))
session_code = (result.json()["data"]["session_code"])

folder_tree_url = "https://www.arista.com/custom_data/api/cvp/getFolderTree/"
jsonpost = {'sessionCode': session_code}
result = requests.post(folder_tree_url, data=json.dumps(jsonpost))
folder_tree = (result.json()["data"]["xml"])

root = ET.fromstring(folder_tree)
path = ""

if i:
   z = 1
   eos_filename = "EOS-" + eos + "-INT.swi"
else:
   z = 0
   eos_filename = "EOS-" + eos + ".swi"

if os.path.isfile(eos_filename):
   print ("\nLocal copy of file already exists")
else:
   for child in root[z].iter('dir'):
      if child.attrib == {'label': "EOS-" + eos}:
         for grandchild in child.iter('file'):
            if grandchild.text == (eos_filename):
               path = grandchild.attrib['path']


   if path == "":
      print("\nEOS image does not exist.")
      sys.exit()
   download_link_url = "https://www.arista.com/custom_data/api/cvp/getDownloadLink/"
   jsonpost = {'sessionCode': session_code, 'filePath': path}
   result = requests.post(download_link_url, data=json.dumps(jsonpost))
   download_link = (result.json()["data"]["url"])

   print(eos_filename + " is currently downloading....")

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

   download_file (download_link, eos_filename)
 
if cvp != '':
   print ("\nUploading " + eos_filename + " to CVP")
   ssh = SSHClient()
   ssh.load_system_host_keys()
   ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   ssh.connect(cvp, username="root", password=rootpw)
   scp = SCPClient(ssh.get_transport())
   scp.put(eos_filename)
   print ("\nFile copied to CVP server")
   stdin, stdout, stderr = ssh.exec_command('python -m SimpleHTTPServer 9999')
   time.sleep(2)
   stdin, stdout, stderr = ssh.exec_command('netstat -tulpn | grep LISTEN | grep 9999')
   out = stdout.read().decode("utf-8")
   if out == '':
      print ("\Web server not started!")
   else:
      print ("\nWeb server started!")

   stdin, stdout, stderr = ssh.exec_command('python /cvpi/tools/imageUpload.py --swiUrl http://localhost:9999/' + eos_filename + ' --bundle EOS-' + eos + ' --user ' + cvp_user + ' --password ' + cvp_passwd)
   exit_status = stdout.channel.recv_exit_status()
   if exit_status == 0:
      print ("\nUpload complete")
   else:
      print ("\nFile not uploaded")
      print (stderr.read())
      print (stdout.read())
      print (stdin.read())
   stdin, stdout, stderr = ssh.exec_command('netstat -tulpn | grep LISTEN | grep 9999')
   out = stdout.read().decode("utf-8")
   print (out)
   print (type(out))
   m = re.search('[0-9]+/python', out)
   pid = m.group().rstrip('/python')
   print (pid)
   stdin, stdout, stderr = ssh.exec_command('kill -hup ' + pid)
   print ('Web Server PID killed')
   if ssh:
      ssh.close()
