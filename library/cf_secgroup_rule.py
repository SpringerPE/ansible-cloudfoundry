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


__program__ = "cf_secgroup_rule"
__version__ = "0.1.1"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_secgroup_rule
short_description: Manage Cloud Foundry Security Group rules
description:
    - Manage Cloud Foundry Security Group rules
author: "Jose Riguera, jose.riguera@springer.com"
options:
    state:
        description:
            - Desired state of the security group rule
        required: false
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the rule
        required: true
        default: null
        aliases: [id]
    sec_group:
        description:
            - Name of the security group where the rule is
        required: true
    protocol:
        description:
            - Rule network protocol
        required: true
        default: all
        choices: [tcp, icmp, udp, all]
    destination:
        description:
            - Rule network destination CIDR
        required: true
        default: '0.0.0.0/0'
    ports:
        description:
            - Port or port list (start-end) (for tcp and udp)
        required: true if tcp or udp
        default: null
    log:
        description:
            - Log matching rule
        required: false
        default: false
    code:
        description:
            - ICMP code
        required: true if icmp
        default: null
    type:
        description:
            - ICMP packet type
        required: true if icmp
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
    force:
        description:
            - Force deletion of entities
        required: false
        default: false
'''

EXAMPLES = '''
- name: create rule test-rule-secgroup-8081 in test-rule-secgroup
  cf_secgroup_rule:
    name: "test-rule-secgroup-8081"
    sec_group: "test-rule-secgroup"
    protocol: tcp
    destination: "127.0.0.1/0"
    ports: "8081"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: delete rule test-rule-secgroup-8081 in test-rule-secgroup
  cf_secgroup_rule:
    name: "test-rule-secgroup-8081"
    sec_group: "test-rule-secgroup"
    state: absent
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
'''

RETURN = '''
...
'''


class CF_Secgroup_rule(object):

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
        self.secg_name = self.module.params['sec_group']

    def run(self):
        state = self.module.params['state']
        try:
            sec_group = self.cf.search_secgroup(self.secg_name)
            if not sec_group:
                self.module.fail_json(msg='Security group not found')
            mode = state == "present"
            sec_group_guid = sec_group['metadata']['guid']
            result = self.set_sec_group_rule(sec_group_guid, mode)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))
        self.module.exit_json(**result)

    def set_sec_group_rule(self, guid, mode):
        rule = {
            'description': self.name,
            'destination': self.module.params['destination'],
            'protocol': self.module.params['protocol'],
            'log': self.module.params['log']
        }
        if self.module.params['ports'] is not None:
            rule['ports'] = self.module.params['ports']
        if self.module.params['code'] is not None:
            rule['code'] = self.module.params['code']
        if self.module.params['type'] is not None:
            rule['type'] = self.module.params['type']
        sec_group = self.cf.manage_secgroup_rule(guid, rule, mode)
        changed = False
        msg = "CF security group %s rules not updated" % (self.name)
        if sec_group is not None:
            changed = True
            msg = "CF security group %s rules updated" % (self.name)
        result = {
            'changed': changed,
            'msg': msg,
            'data': sec_group
        }
        return result


def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='present', type='str', choices=['present', 'absent']),
            name = dict(required=True, type='str', aliases=['id']),
            admin_user = dict(required=True, type='str'),
            admin_password = dict(required=True, type='str', no_log=True),
            api_url = dict(required=True, type='str'),
            sec_group = dict(required=True, type='str'),
            protocol = dict(default='all', type='str', choices=['tcp', 'icmp', 'udp', 'all']),
            destination = dict(default='0.0.0.0/0', type='str'),
            ports = dict(required=False, type='str'),
            log = dict(default=False, type='bool'),
            code = dict(required=False, type='int'),
            type = dict(required=False, type='int'),
            force = dict(default=False, type='bool'),
        ),
        supports_check_mode = True,
        required_if = [
            ["protocol", "icmp", ["type", "code"] ],
        ],
        mutually_exclusive = [
            ["type", "ports"]
        ],
        required_together = [
            ["type", "code"]
        ]
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_Secgroup_rule(module)
    cf.run()


if __name__ == '__main__':
    main()
