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


__program__ = "cf_config"
__version__ = "0.1.1"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_config
short_description: Manage Cloud Foundry config
description:
    - Manage Cloud Foundry configuration:
    feature-flags, environment-variable-groups
    and default security-groups
requirements:
    - python-cfconfigurator
author: "Jose Riguera, jose.riguera@springer.com"
options:
    state:
        description:
            - Desired state of the entity
        required: false
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the entity
        required: true
        default: null
        aliases: [id]
    value:
        description:
            - Value of the entity
        required: False
        default: null
    context:
        description:
            - For env-vars and sec-groups context
        default: running
        choices: [running, staging]
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
            - Force deletion of the entities
        required: false
        default: false
'''

EXAMPLES = '''
- name: enable user_org_creation
  cf_config:
    type: feature_flag
    name: "user_org_creation"
    value: true
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: define env variable MY_HOME=Rotterdam on running context
  cf_config:
    type: env_var
    name: "MY_HOME"
    value: "Rotterdam"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: set test-secgroup as default for staging
  cf_config:
    type: sec_group
    name: "test-secgroup"
    context: staging
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
'''

RETURN = '''
...
'''


class CF_Config(object):

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
        state = self.module.params['state']
        config_type = self.module.params['type']
        mode = True if state == "present" else False
        try:
            if config_type == "feature_flag":
                if self.module.params['value'] is None:
                    mode = self.module.boolean(self.module.params['value'])
                result = self.set_flag(mode)
            elif config_type == "env_var":
                if self.module.params['value'] is None:
                    self.module.fail_json(msg="No value for env var %s" % self.name)
                result = self.set_env(mode)
            elif config_type == "sec_group":
                result = self.set_sec_group(mode)
            else:
                self.module.fail_json(msg='Invalid type: %s' % config_type)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))
        self.module.exit_json(**result)

    def set_flag(self, status):
        flags = self.cf.get_feature_flags()
        for f in flags:
            if f['name'] == self.name:
                break
        else:
            msg = 'Feature flag not found: %s' % (self.name)
            self.module.fail_json(msg=msg)
        changed = self.cf.manage_feature_flags(self.name, status)
        result = {
            'changed': changed,
            'msg': "CF feature flag %s: %s" % (self.name, status)
        }
        return result

    def set_env(self, add):
        context = self.module.params['context']
        value = self.module.params['value']
        changed = self.cf.manage_variable_group(self.name, value, context, add)
        result = {
            'changed': changed,
            'msg': "CF environment variable group %s: %s" % (self.name, value)
        }
        return result

    def set_sec_group(self, add):
        sec_group = self.cf.search_secgroup(self.name)
        if sec_group is None:
            self.module.fail_json(msg="Security group %s not found" % self.name)
        sec_group_guid = sec_group['metadata']['guid']
        context = self.module.params['context']
        changed = self.cf.manage_secgroup_defaults(sec_group_guid, context, add)
        result = {
            'changed': changed,
            'msg': "CF sec group %s default %s group: %s" % (self.name, context, changed)
        }
        return result


def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='present', type='str', choices=['present', 'absent']),
            name = dict(required=True, type='str', aliases=['id']),
            admin_user = dict(required=True, type='str'),
            admin_password  = dict(required=True, type='str', no_log=True),
            api_url = dict(required=True, type='str'),
            type = dict(default='feature_flag', type='str', choices=['feature_flag', 'env_var', 'sec_group']),
            value = dict(required=False, type='str'),
            context = dict(default='running', type='str', choices=['running', 'staging']),
            validate_certs = dict(default=False, type='bool'),
            force = dict(default=False, type='bool'),
        ),
        supports_check_mode = True,
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_Config(module)
    cf.run()


if __name__ == '__main__':
    main()
