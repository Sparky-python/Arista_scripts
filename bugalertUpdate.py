#!/usr/bin/env python
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
3. run the script with.. ./bugalertUpdate.py --api <BUGALERTS TOKEN FROM ARISTA.COM> --cvp <CVP SERVER IP ADDRESS> --rootpw <ROOT PASSWORD OF CVP SERVER>
4. python pip install scp, paramiko

Credit to Corey Hinds for original script which this was based on to update BugAlerts file 
in CVX
"""
__author__ = 'marayson'

import base64
import json
import warnings
import requests
import argparse
import sys
from paramiko import SSHClient
from scp import SCPClient
import paramiko
import os


warnings.filterwarnings("ignore")
parser = argparse.ArgumentParser()
parser.add_argument('--api', required=False,
                    default='2beb105836a4c44b942eed4666d0cd48', help='arista.com user API key')
parser.add_argument('--cvp', required=False,
                    default='192.168.32.10', help='IP address of CVP server')
parser.add_argument('--rootpw', required=False,
                    default='Arista123', help='Root password of CVP server')

args = parser.parse_args()

api = args.api
cvp = args.cvp
rootpw = args.rootpw


creds = (base64.b64encode(api.encode())).decode("utf-8")

url = 'https://www.arista.com/custom_data/bug-alert/alertBaseDownloadApi.php'

warnings.filterwarnings("ignore")

jsonpost = {'token_auth': creds, 'file_version':'2'}

result = requests.post(url, data=json.dumps(jsonpost))
web_data = json.loads(result.text)
web_data_final = result.text
split_web_data = web_data_final.splitlines()

alertBaseFile = 'AlertBase-CVP.json'

#try:
#    with open(alertBaseFile) as filetest:
#        # Check if the AlertBase JSON file exists
#        pass
#except IOError as e:
#    # handle the exception (file doesn't exist) by downloading the AlertBase JSON
#    print ('\n Bug Alert Database does not exist. Downloading...\n')
#    alertdbfile = open(alertBaseFile, 'w')
#    alertdbfile.write(web_data_final)
#    alertdbfile.close()
#    print('\n Bug Alert Database successfully created and imported\n')
#    exit(0)

if os.path.isfile(alertBaseFile):
   with open(alertBaseFile, 'r') as file:
      existing_file = file.read()
   split_existing_file = existing_file.splitlines()
   if split_web_data[2] != split_existing_file[2]: 
      existing_file.close()   
      os.remove('AlertBase-CVP.json')

      print ('\n Bug Alert Database out of date. Downloading update...\n')
      alertdbfile = open(alertBaseFile, 'w')
      alertdbfile.write(web_data_final)
      alertdbfile.close()
      print('\n Bug Alert Database successfully created and imported\n')

      ssh = SSHClient()
      ssh.load_system_host_keys()
      ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      ssh.connect(cvp, username="root", password=rootpw)
      scp = SCPClient(ssh.get_transport())
      scp.put('AlertBase-CVP.json')
      stdin, stdout, stderr = ssh.exec_command('chmod 644 AlertBase-CVP.json')
      stdin, stdout, stderr = ssh.exec_command('mv -f AlertBase-CVP.json /cvpi/apps/aeris/bugalerts/AlertBase.json')
      stdin, stdout, stderr = ssh.exec_command('su cvp')
      stdin, stdout, stderr = ssh.exec_command('cvpi stop bugalerts-update && cvp start bugalerts-update')
   else:
      print('\n No updates to Bug Alert Database file.\n')
else:
   print ('\n Bug Alert Database does not exist. Downloading...\n')
   alertdbfile = open(alertBaseFile, 'w')
   alertdbfile.write(web_data_final)
   alertdbfile.close()
   print('\n Bug Alert Database successfully created and imported\n')

   ssh = SSHClient()
   ssh.load_system_host_keys()
   ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   ssh.connect(cvp, username="root", password=rootpw)
   scp = SCPClient(ssh.get_transport())
   scp.put('AlertBase-CVP.json')
   stdin, stdout, stderr = ssh.exec_command('chmod 644 AlertBase-CVP.json')
   stdin, stdout, stderr = ssh.exec_command('mv -f AlertBase-CVP.json /cvpi/apps/aeris/bugalerts/AlertBase.json')
   stdin, stdout, stderr = ssh.exec_command('su cvp')
   stdin, stdout, stderr = ssh.exec_command('cvpi stop bugalerts-update && cvp start bugalerts-update')
   

