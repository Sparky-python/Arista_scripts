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

def viewBar(a,b):
    # original version
    res = a/int(b)*100
    sys.stdout.write('\rComplete precent: %.2f %%' % (res))
    sys.stdout.flush()

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


warnings.filterwarnings("ignore")
parser = argparse.ArgumentParser()
parser.add_argument('--api', required=True,
                    default='', help='arista.com user API key')
parser.add_argument('--file', required=True, action='append',
                    default=[], help='EOS and swix iamges to download, repeat --file option for each file. EOS images should be in the form 4.22.1F for normal images, 4.22.1F-INT for the international/federal version and TerminAttr-1.7.4 for TerminAttr files')
parser.add_argument('--cvp', required=False,
                    default='', help='IP address of CVP server')
parser.add_argument('--rootpw', required=False,
                    default='', help='Root password of CVP server')
parser.add_argument('--cvp_user', required=False,
                    default='', help='CVP WebUI Username')
parser.add_argument('--cvp_passwd', required=False,
                    default='', help='CVP WebUI Password')

args = parser.parse_args()

api = args.api
cvp = args.cvp
rootpw = args.rootpw
cvp_user = args.cvp_user
cvp_passwd = args.cvp_passwd
file_list = args.file

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

for image in file_list:
   if "-INT" in image:
      z = 1
      eos_filename = "EOS-" + image + ".swi"
      image = image.rstrip("-INT")
   elif "TerminAttr" in image:
      z = 3
      eos_filename = image + "-1.swix"
   else:
      z = 0
      eos_filename = "EOS-" + image + ".swi"

   if os.path.isfile(eos_filename):
      print ("\nLocal copy of file already exists")
   else:
      for child in root[z].iter('dir'):
         if child.attrib == {'label': "EOS-" + image}:
            for grandchild in child.iter('file'):
               if grandchild.text == (eos_filename):
                  path = grandchild.attrib['path']
         elif child.attrib == {'label': image} or child.attrib == {'label': image + "-1"}  :
            print (child.attrib)
            for grandchild in child.iter('file'):
               if grandchild.text == (eos_filename):
                  path = grandchild.attrib['path']



      if path == "":
         print("\nFile " + eos_filename +" does not exist.")
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

   if eos_filename and terminattr_filename:
      stdin, stdout, stderr = ssh.exec_command('python /cvpi/tools/imageUpload.py --swi ' + eos_filename + ' --swix ' + terminattr_filename + ' --bundle EOS-' + eos_bundle + ' --user ' + cvp_user + ' --password ' + cvp_passwd)
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
