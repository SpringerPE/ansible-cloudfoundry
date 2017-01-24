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


__program__ = "cf_quota"
__version__ = "0.1.1"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_quota
short_description: Manage Cloud Foundry Quotas
description:
    - Manage Cloud Foundry Quotas
author: "Jose Riguera, jose.riguera@springer.com"
options:
    state:
        description:
            - Desired state of the quota
        required: false
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the org
        required: true
        default: null
        aliases: [id]
    non_basic_services_allowed:
        description:
            - Amount of non_basic_services_allowed
        required: true
    total_services:
        description:
            - Amount of total_services
        required: true
    total_routes:
        description:
            - Amount of total routes
        required: true
    memory_limit:
        description:
            - Memory limit in MB
        required: true
    instance_memory_limit:
        description:
            - Memory limit by instance in MB
        required: true
    total_service_keys:
        description:
            - Total service keys
        required: false
    total_reserved_route_ports:
        description:
            - Total reserved route ports
        required: false
    total_private_domains:
        description:
            - Total private domains
        required: false
    app_instance_limit:
        description:
            - App instance limit
        required: false
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
            - Force deletion of system quota (default)
        required: false
        default: false
'''

EXAMPLES = '''
- name: create quota test-quota
  cf_quota:
    name: "test-quota"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
    non_basic_services_allowed: true
    total_services: 34
    total_routes: 311
    memory_limit: 3200
    instance_memory_limit: 3100
    total_service_keys: 37
    total_reserved_route_ports: 38
    total_private_domains: 39
    app_instance_limit: 310

- name: delete quota test-quota
  cf_quota:
    name: "test-quota"
    state: absent
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
'''

RETURN = '''
...
'''


class CF_Quota(object):
    system_quotas = ['default']

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

    def run(self):
        force = self.module.params['force']
        state = self.module.params['state']
        try:
            quota = self.cf.search_quota(self.name)
            if state == 'present':
                result = self.present(quota)
            elif state == 'absent':
                if self.name in self.system_quotas and not force:
                    self.module.fail_json(msg="Cannot delete system default quota")
                result = self.absent(quota)
            else:
                self.module.fail_json(msg='Invalid state: %s' % state)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))
        self.module.exit_json(**result)

    def absent(self, quota, async=False):
        changed = False
        if quota is not None:
            quota_guid = quota['metadata']['guid']
            changed = True
            if not self.module.check_mode:
                try:
                    self.cf.delete_quota(quota_guid, async)
                except CFException as e:
                    msg = 'Cannot delete quota %s: %s' % (self.name, str(e))
                    self.module.fail_json(msg=msg)
        result = {
            'changed': changed,
            'msg': "CF quota %s deleted" % self.name
        }
        return result

    def present(self, quota):
        changed = False
        if quota is None:
            changed = True
            if not self.module.check_mode:
                try:
                    quota = self.cf.save_quota(self.name,
                        self.module.params['non_basic_services_allowed'],
                        self.module.params['total_services'],
                        self.module.params['total_routes'],
                        self.module.params['memory_limit'],
                        self.module.params['instance_memory_limit'],
                        self.module.params['total_service_keys'],
                        self.module.params['total_reserved_route_ports'],
                        self.module.params['total_private_domains'],
                        self.module.params['app_instance_limit'])
                except CFException as e:
                    msg = "Cannot create quota %s: %s" % (self.name, str(e))
                    self.module.fail_json(msg=msg)
            msg = "CF quota %s created" % self.name
        else:
            guid = quota['metadata']['guid']
            quota_list = [
                'non_basic_services_allowed',
                'total_services',
                'total_routes',
                'memory_limit',
                'instance_memory_limit',
                'total_service_keys',
                'total_reserved_route_ports',
                'total_private_domains',
                'app_instance_limit'
            ]
            for item in quota_list:
                if self.module.params[item] != quota['entity'][item]:
                    changed = True
                    break
            if changed:
                if not self.module.check_mode:
                    try:
                        quota = self.cf.save_quota(self.name,
                            self.module.params['non_basic_services_allowed'],
                            self.module.params['total_services'],
                            self.module.params['total_routes'],
                            self.module.params['memory_limit'],
                            self.module.params['instance_memory_limit'],
                            self.module.params['total_service_keys'],
                            self.module.params['total_reserved_route_ports'],
                            self.module.params['total_private_domains'],
                            self.module.params['app_instance_limit'],
                            guid)
                    except CFException as e:
                        msg = "Cannot update quota %s: %s" % (self.name, str(e))
                        self.module.fail_json(msg=msg)
                msg = "CF quota %s updated" % self.name
            else:
                msg = "CF quota %s not updated" % self.name
        result = {
            'changed': changed,
            'msg': msg,
            'data': quota
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
            non_basic_services_allowed = dict(type='bool'),
            total_services = dict(type='int'),
            total_routes = dict(type='int'),
            memory_limit = dict(type='int'),
            instance_memory_limit = dict(type='int'),
            total_service_keys = dict(default=-1, type='int'),
            total_reserved_route_ports = dict(default=0, type='int'),
            total_private_domains = dict(default=-1, type='int'),
            app_instance_limit = dict(default=-1, type='int'),
            validate_certs  = dict(default=False, type='bool'),
            force = dict(default=False, type='bool'),
        ),
        supports_check_mode = True,
        required_if = [
            [ "state", "present", [
                "non_basic_services_allowed",
                "total_services",
                "total_routes",
                "memory_limit",
                "instance_memory_limit",
                ]
            ],
            [ "state", "absent", [] ]
        ]
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_Quota(module)
    cf.run()


if __name__ == '__main__':
    main()
