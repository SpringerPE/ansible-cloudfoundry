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


__program__ = "cf_user"
__version__ = "0.1.0"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_user
short_description: Manage Cloud Foundry Users
description:
    - Manage Cloud Foundry Users
author: "Jose Riguera, jose.riguera@springer.com"
options:
    state:
        description:
            - Desired state of the user
        required: false
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the user
        required: true
        default: null
        aliases: [id]
    organization:
        description:
            - Name of the quota asigned to the org
        required: false
        default: "default"
    space:
        description:
            - Name of the quota asigned to the org
        required: false
        default: "default"
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
            - Force deletion of a user or password update
        required: false
        default: false
'''

EXAMPLES = '''
- name: create user test
  cf_user:
    name: "test"
    quota: "default"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
'''

RETURN = '''
...
'''


class CF_User(object):

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
            user = self.cf.search_user(self.name)
            if state == 'present':
                space_guid = None
                if self.module.params['default_organization'] is not None:
                    org = self.cf.search_org(self.module.params['default_organization'])
                    if not org:
                        self.module.fail_json(msg='Organization not found')
                    org_guid = org['metadata']['guid']
                    space_name = self.module.params['default_space']
                    space = self.cf.search_space(org_guid, space_name)
                    if not space:
                        self.module.fail_json(msg='Space not found')
                    space_guid = space['metadata']['guid']
                result = self.present(user, space_guid, force)
            elif state == 'absent':
                result = self.absent(user, True)
            else:
                self.module.fail_json(msg='Invalid state: %s' % state)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            raise
            self.module.fail_json(msg="Exception: %s" % str(e))
        self.module.exit_json(**result)

    def absent(self, user, force, async=False):
        changed = False
        if user is not None:
            user_id = user['metadata']['guid']
            changed = True
            if not self.module.check_mode:
                try:
                    self.cf.delete_user(user_id, async, force)
                except CFException as e:
                    msg = 'Cannot delete user %s: %s' % (self.name, str(e))
                    self.module.fail_json(msg=msg)
        result = {
            'changed': changed,
            'msg': "CF user %s deleted" % self.name
        }
        return result

    def present(self, user, default_space_guid, force):
        changed = True
        user_id = None
        if user is not None:
            user_id = user['metadata']['guid']
            if user['entity']['default_space_guid'] == default_space_guid:
                changed = False
        if not self.module.check_mode:
            try:
                changed_user, user = self.cf.save_user(self.name,
                    self.module.params['given_name'],
                    self.module.params['family_name'],
                    self.module.params['email'],
                    self.module.params['password'],
                    self.module.params['active'],
                    self.module.params['origin'],
                    self.module.params['external_id'],
                    default_space_guid,
                    force, user_id)
            except CFException as e:
                msg = "Cannot create user %s: %s" % (self.name, str(e))
                self.module.fail_json(msg=msg)
            msg = "CF user %s updated: %s" % (self.name, changed_user)
        result = {
            'changed': changed or changed_user,
            'msg': msg,
            'data': user
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
            email = dict(type='str'),
            given_name = dict(type='str'),
            family_name = dict(type='str'),
            password = dict(type='str', no_log=True),
            active = dict(default=True, type='bool'),
            origin = dict(default='uaa', type='str'),
            external_id = dict(type='str'),
            default_organization = dict(required=False, type='str'),
            default_space = dict(required=False, type='str'),
            validate_certs = dict(default=False, type='bool'),
            force = dict(default=False, type='bool'),
        ),
        supports_check_mode = True,
        required_if = [
            [ "state", "present", [
                "given_name",
                "family_name",
                ]
            ],
            [ "state", "absent", [] ]
        ],
        required_together = [
            ['default_organization', 'default_space']
        ]
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_User(module)
    cf.run()


if __name__ == '__main__':
    main()
