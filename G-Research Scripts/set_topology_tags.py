#!/usr/bin/env python3
# #
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
# create_eapi_conf.py
#
#    Written by:
#       Mark Rayson, Arista Networks
#
 

from getpass import getpass
import pprint
import ssl
from cvprac.cvp_client import CvpClient
import re
import argparse

def get_active_devices(client):
    ''' Get active devices '''
    dev_url = '/api/resources/inventory/v1/Device/all'
    devices_data = client.get(dev_url)
    devices = []
    for device in devices_data['data']:
        try:
            if device['result']['value']['streamingStatus'] == "STREAMING_STATUS_ACTIVE":
                devices.append(device['result']['value'])
        # pass on archived datasets
        except KeyError as e:
            continue
    return devices

def assign_dtag(client, dId, label, value):
    tag_url = '/api/resources/tag/v1/DeviceTagAssignmentConfig'
    payload = {"key":{"label":label, "value":value, "deviceId": dId}}
    response = client.post(tag_url, data=payload)
    return response

def create_dtag(client, label, value):
    tag_url = '/api/resources/tag/v1/DeviceTagConfig'
    payload = {"key":{"label":label,"value":value}}
    response = client.post(tag_url, data=payload)
    return response

def get_all_device_tags(client):
    tag_url = '/api/resources/tag/v1/DeviceTag/all'
    tag_data = client.get(tag_url)
    tags = []
    for tag in tag_data['data']:
        tags.append({tag['result']['value']['key']['label']:tag['result']['value']['key']['value']})
    return tags

def get_device_tag(client, dId=None, label=None, value=None):
    tag_url = '/api/resources/tag/v1/DeviceTagAssignmentConfig/all'
    payload = {
                "partialEqFilter": [
                    {"key": {"deviceId": dId, "label": label, "value": value}}
                ]
            }
    response = client.post(tag_url, data=payload)
    return response

def get_datacenter(hostname):
    datacenter = hostname.split('-')[2]
    return datacenter

def get_rack(hostname):
    rack = hostname.split('-')[1]
    return rack

def get_device_type(hostname):
    device_type = hostname.split('-')[0]
    if "Spine" in device_type:
        return "spine"
    if "Leaf" in device_type or "BL" in device_type:
        return "leaf"
    return device_type

def in_dictlist(key, value, my_dictlist):
    for this in my_dictlist:
        if this[key] == value:
            return this
    return {}

def check_hostname_format(hostname):
    return re.match("^([0-9]|[A-Z]|[a-z])+-([0-9]|[A-Z])+-([0-9]|[A-Z])+$", hostname)

ssl._create_default_https_context = ssl._create_unverified_context
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

parser = argparse.ArgumentParser()
parser.add_argument('--cvp', required=True,
                    default='', help='IP Address of CVP server')
parser.add_argument('--user', required=True,
                    default='', help='CVP Username')

args = parser.parse_args()
cvp = args.cvp
user = args.user
passwd = getpass(prompt='CVP password for user {}: '.format(user))

clnt = CvpClient()
clnt.connect([cvp], user, passwd)

list_of_devices = get_active_devices(clnt)

list_of_tags = get_all_device_tags(clnt)

for device in list_of_devices:
    if check_hostname_format(device['hostname']):
        print(get_device_tag(clnt, dId=device['key']['deviceId'], label="topology_hint_type", value=get_device_type(device['hostname'])))
        print ("Setting " + device['hostname'] + " device type to " + get_device_type(device['hostname']) + ", deviceID is " + device['key']['deviceId'])
        if not any(d.get("topology_hint_type") == get_device_type(device['hostname']) for d in list_of_tags):
            create_dtag(clnt, "topology_hint_type", get_device_type(device['hostname']))
        if (get_device_tag(clnt, dId=device['key']['deviceId'], label="topology_hint_type", value=get_device_type(device['hostname']))) == {'data': ''}:
            assign_dtag(clnt, device['key']['deviceId'], "topology_hint_type", get_device_type(device['hostname']))
        list_of_tags = get_all_device_tags(clnt)
        #assign_dtag(clnt, device, "topology_hint_rack", get_rack(device['hostname']) )
        print ("Setting " + device['hostname'] + " datacenter to " + get_datacenter(device['hostname']) + ", deviceID is " + device['key']['deviceId'])
        if not any(d.get("topology_hint_datacenter") == get_datacenter(device['hostname']) for d in list_of_tags):
            create_dtag(clnt, "topology_hint_datacenter", get_datacenter(device['hostname']))
        if (get_device_tag(clnt, dId=device['key']['deviceId'], label="topology_hint_datacenter", value=get_datacenter(device['hostname']))) == {'data': ''}:
            assign_dtag(clnt, device['key']['deviceId'], "topology_hint_datacenter", get_datacenter(device['hostname']))
        list_of_tags = get_all_device_tags(clnt)
