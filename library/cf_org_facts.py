#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ansible-cloudfoundry is a set of modules to manage Cloud Foundry with Ansible
(c) 2016 Jose Riguera Lopez, jose.riguera@springer.com

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals, print_function
import sys

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from ansible.module_utils.basic import AnsibleModule

try:
    from cfconfigurator.cf import CF
    from cfconfigurator.exceptions import CFException
except ImportError:
    cfconfigurator_found = False
else:
    cfconfigurator_found = True


__program__ = "cf_org_facts"
__version__ = "0.1.0"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_org_facts
short_description: Get facts from Cloud Foundry Orgs
description:
    - Get facts from Cloud Foundry Orgs
author: "Jose Riguera, jose.riguera@springer.com"
options:
    name:
        description:
            - Name of the org to retrieve facts for, if omitted will return a list of all orgs the given user has access to
        required: false
        default: null
        aliases: [id]
    space:
        description:
            - Name of the space within the org to retrive facts for
        required: false
        default: null
    admin_user:
        description:
            - Administrator username/email
        required: true
        default: null
    admin_password:
        description:
            - Administrator password
        required: true
        default: null
    api_url:
        description:
            - URL of api end point
        required: true
    validate_certs:
        description:
            - Validate SSL certs. Validation will fail with self-signed certificates.
        required: false
        default: false
'''

EXAMPLES = '''
- name: retrive facts about an org called 'test'
  cf_org_facts:
    name: "test"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
  register: result

- name: retrive a list of all available org names
  cf_org_facts:
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
  register: result
'''

RETURN = '''
    # Response for Example 1
    {
        "ansible_facts": {
            "allow_ssh": false,
            "created_at": "2016-11-17T14:42:45Z",
            "guid": "ea12517c-2610-4294-a291-e1aa0af9b170",
            "name": "test",
            "quota": {},
            "sec_groups": [
                {
                    "created_at": "2016-11-08T14:30:40Z",
                    "guid": "2f757c5f-9a02-47b5-a467-96f1a45e8882",
                    "name": "public_networks",
                    "rules": [
                        {
                            "destination": "0.0.0.0-9.255.255.255",
                            "protocol": "all"
                        },
                        {
                            "destination": "11.0.0.0-169.253.255.255",
                            "protocol": "all"
                        },
                        {
                            "destination": "169.255.0.0-172.15.255.255",
                            "protocol": "all"
                        },
                        {
                            "destination": "172.32.0.0-192.167.255.255",
                            "protocol": "all"
                        },
                        {
                            "destination": "192.169.0.0-255.255.255.255",
                            "protocol": "all"
                        }
                    ],
                    "running_default": true,
                    "staging_default": true,
                    "updated_at": null
                },
                {
                    "created_at": "2016-11-08T14:30:40Z",
                    "guid": "9b40d9b3-77c7-45e1-96ea-5f41de72fd09",
                    "name": "dns",
                    "rules": [
                        {
                            "destination": "0.0.0.0/0",
                            "ports": "53",
                            "protocol": "tcp"
                        },
                        {
                            "destination": "0.0.0.0/0",
                            "ports": "53",
                            "protocol": "udp"
                        }
                    ],
                    "running_default": true,
                    "staging_default": true,
                    "updated_at": null
                },
                {
                    "created_at": "2016-11-08T14:30:40Z",
                    "guid": "dc52eaf9-068b-4b53-bc52-c1334266dbc9",
                    "name": "private_networks",
                    "rules": [
                        {
                            "destination": "10.0.0.0-10.255.255.255",
                            "protocol": "all"
                        },
                        {
                            "destination": "172.16.0.0-172.31.255.255",
                            "protocol": "all"
                        },
                        {
                            "destination": "192.168.0.0-192.168.255.255",
                            "protocol": "all"
                        }
                    ],
                    "running_default": true,
                    "staging_default": false,
                    "updated_at": null
                },
                {
                    "created_at": "2016-11-22T15:46:08Z",
                    "guid": "baf4373c-8897-4371-848a-5bbfb4e7e758",
                    "name": "sec1",
                    "rules": [
                        {
                            "description": "allow-proxy",
                            "destination": "127.0.0.1/0",
                            "log": false,
                            "ports": "8081",
                            "protocol": "tcp"
                        }
                    ],
                    "running_default": true,
                    "staging_default": false,
                    "updated_at": "2016-11-22T15:46:12Z"
                }
            ],
            "updated_at": null,
            "users": {
                "auditors": [],
                "developers": [],
                "managers": []
            }
        },
        "changed": false
    }

    # Response for Example 2
    {
        "ansible_facts": {
            "orgs": []
        },
        "changed": false
    }
'''


class CF_Org_Facts(object):
    def __init__(self, module):
        self.module = module
        admin_user = self.module.params['admin_user']
        admin_password = self.module.params['admin_password']
        api_url = self.module.params['api_url']
        self.name = self.module.params['name']
        try:
            self.cf = CF(api_url)
            self.cf.login(admin_user, admin_password)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))

    def get_all_orgs(self):
        all_orgs = []
        # raise Exception(self.cf.api_url + '/v2/organizations')
        response, rcode = self.cf.request('GET', self.cf.api_url + '/v2/organizations')
        # raise Exception(response)
        if rcode == 200:
            return [ org['entity']['name'] for org in response['resources'] ]

    def get_quota(self, url):
        facts = {}
        quota, rcode = self.cf.request('GET', self.cf.api_url + url)
        if rcode == 200:
            facts['guid'] = quota['metadata']['guid']
            facts['created_at'] = quota['metadata']['created_at']
            facts['updated_at'] = quota['metadata']['updated_at']
            for key in quota['entity']:
                facts[key] = quota['entity'][key]
        return facts

    def get_private_domains(self, url, org_owner=None):
        owner_domains = []
        shared_domains = []
        domains, rcode = self.cf.request('GET', self.cf.api_url + url)
        if rcode == 200:
            for domain in domains['resources']:
                fact = {}
                fact['guid'] = domain['metadata']['guid']
                fact['created_at'] = domain['metadata']['created_at']
                fact['updated_at'] = domain['metadata']['updated_at']
                fact['name'] = domain['entity']['name']
                if org_id_owner is not None and domain['entity']['owning_organization_guid'] == org_owner:
                    owner_domains.append(fact)
                else:
                    shared_domains.append(fact)
        facts = {
            'owner_domains': owner_domains,
            'shared_domains': shared_domains
        }
        return facts

    def get_users(self, url):
        facts = []
        users, rcode = self.cf.request('GET', self.cf.api_url + url)
        if rcode == 200:
            for user in users['resources']:
                fact = {}
                fact['guid'] = user['metadata']['guid']
                fact['created_at'] = user['metadata']['created_at']
                fact['updated_at'] = user['metadata']['updated_at']
                fact['name'] = user['entity']['username']
                fact['admin'] = user['entity']['admin']
                fact['active'] = user['entity']['active']
                facts.append(fact)
        return facts

    def get_secgroups(self, url):
        facts = []
        secgroups, rcode = self.cf.request('GET', self.cf.api_url + url)
        if rcode == 200:
            for sg in secgroups['resources']:
                fact = {}
                fact['guid'] = sg['metadata']['guid']
                fact['created_at'] = sg['metadata']['created_at']
                fact['updated_at'] = sg['metadata']['updated_at']
                fact['name'] = sg['entity']['name']
                fact['running_default'] = sg['entity']['running_default']
                fact['staging_default'] = sg['entity']['staging_default']
                fact['rules'] = sg['entity']['rules']
                facts.append(fact)
        return facts

    def get_spaces(self, url, space_name=None, users_type=['developers', 'managers', 'auditors']):
        facts = []
        spaces, rcode = self.cf.request('GET', self.cf.api_url + url)
        if rcode == 200:
            for space in spaces['resources']:
                if space_name is not None and space['entity']['name'] != space_name:
                    break
                fact = {}
                fact['guid'] = space['metadata']['guid']
                fact['created_at'] = space['metadata']['created_at']
                fact['updated_at'] = space['metadata']['updated_at']
                fact['name'] = space['entity']['name']
                fact['allow_ssh'] = space['entity']['allow_ssh']
                if 'quota_definition_url' in space['entity']:
                    fact['quota'] = self.get_quota(space['entity']['quota_definition_url'])
                else:
                    fact['quota'] = {}
                fact['sec_groups'] = self.get_secgroups(space['entity']['security_groups_url'])
                fact['users'] = {}
                for user_type in users_type:
                    if user_type not in fact['users']:
                        fact['users'][user_type] = []
                    user_url = user_type + '_url'
                    if user_url in space['entity']:
                        fact['users'][user_type] = self.get_users(space['entity'][user_url])
                facts.append(fact)
        return facts

    def run(self):
        facts = {}
        try:
            space_name = self.module.params['space']
            if self.name is not None:
                org = self.cf.search_org(self.name)
                if org is not None:
                    if space_name is not None:
                        facts = self.get_spaces(org['entity']['spaces_url'], space_name)[0]
                    else:
                        facts['name'] = org['entity']['name']
                        facts['guid'] = org['metadata']['guid']
                        facts['status'] = org['entity']['status']
                        facts['created_at'] = org['metadata']['created_at']
                        facts['updated_at'] = org['metadata']['updated_at']
                        facts['spaces'] = self.get_spaces(org['entity']['spaces_url'])
                        if 'quota_definition_url' in org['entity']:
                            facts['quota'] = self.get_quota(org['entity']['quota_definition_url'])
                        else:
                            facts['quota'] = {}
                        facts['users'] = {}
                        for user_type in ['users', 'managers', 'billing_managers', 'auditors']:
                            if user_type not in facts['users']:
                                facts['users'][user_type] = []
                            user_url = user_type + '_url'
                            if user_url in org['entity']:
                                facts['users'][user_type] = self.get_users(org['entity'][user_url])
                        domains = self.get_private_domains(org['entity']['private_domains_url'], facts['guid'])
                        facts.update(domains)
            else:
                facts['orgs'] = self.get_all_orgs()
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))
        result = {'ansible_facts': facts}
        self.module.exit_json(**result)


def main():
    module = AnsibleModule(
        argument_spec = dict(
            name = dict(required=False, type='str', aliases=['id']),
            space = dict(required=False, type='str'),
            admin_user = dict(required=True, type='str'),
            admin_password  = dict(required=True, type='str', no_log=True),
            api_url = dict(required=True, type='str'),
            validate_certs = dict(default=False, type='bool'),
        ),
        supports_check_mode = True,
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_Org_Facts(module)
    cf.run()


if __name__ == '__main__':
    main()
