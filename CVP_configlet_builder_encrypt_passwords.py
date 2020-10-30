#
# Copyright (c) 2020, Arista Networks, Inc.
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
# 
#
#    Written by:
#       Mark Rayson, Arista Networks
#
"""
DESCRIPTION
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

"""
__author__ = 'marayson'

from cvplibrary import CVPGlobalVariables,GlobalVariableNames
from cvprac.cvp_client import CvpClient
import crypt
import ssl

try:
  _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
# Legacy Python that doesn't verify HTTPS certificates by default
  pass
else:
# Handle target environment that doesn't support HTTPS verification
  ssl._create_default_https_context = _create_unverified_https_context

ssl._create_default_https_context = ssl._create_unverified_context
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

cvp_username = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
cvp_password = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)

clnt = CvpClient()
clnt.connect(['localhost'], cvp_username, cvp_password)
configlet_name = "cvp_1_site_users_pwd_config"

output = clnt.api.get_configlet_by_name(name = configlet_name)
config = output["config"]
key = output["key"]

new_config = ""

for line in config.splitlines():
  if "secret" in line or "enable" in line:
    words = line.split()
    for x in range(len(words)):
      if words[x] == "secret" and words[x+1] != "sha512":
        words[x+1] = "sha512 " + crypt.crypt(words[x+1], "$6$saltsalt$")
      elif words[x] == "enable" and words[x+1] == "password" and words[x+2] != "sha512":
        words[x+2] = "sha512 " + crypt.crypt(words[x+2], "$6$saltsalt$")
    line = " ".join(words)
    new_config += line + "\n"
  else:
    new_config += line + "\n"

clnt.api.update_configlet(config=new_config, key = key, name = configlet_name)

print "Configlet %s updated. Please now add the Tasks created to a Change Control and execute" % (configlet_name)