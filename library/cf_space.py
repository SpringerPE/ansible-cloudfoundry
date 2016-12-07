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


__program__ = "cf_space"
__version__ = "0.1.1"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_space
short_description: Manage Cloud Foundry Spaces
description:
    - Manage Cloud Foundry Spaces
author: "Jose Riguera, jose.riguera@springer.com"
options:
    state:
        description:
            - Desired state of the Space
        required: false
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the Space
        required: true
        default: null
        aliases: [id]
    organization:
        description:
            - Name of the organization
        required: true
    allow_ssh:
        description:
            - Allow ssh
        required: false
        default: false
    user_name:
        description:
            - Name of the user to add/remove to the space
        required: false
    user_role:
        description:
            - Role of the user in the space
        required: false
        default: "user"
        choices=[user, manager, auditor]
    user_state:
        description:
            - Desired state of the space
        required: false
        default: present
        choices: [present, absent]
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
            - Force deletion of system org and recursive entities in an space
        required: false
        default: false
'''

EXAMPLES = '''
- name: create space stest in test org
  cf_space:
    name: "stest"
    organization: "test"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: delete space stest
  cf_space:
    name: "stest"
    organization: "test"
    state: absent
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
'''

RETURN = '''
...
'''


class CF_Space(object):

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
        self.oname = self.module.params['organization']

    def run(self):
        state = self.module.params['state']
        try:
            org = self.cf.search_org(self.oname)
            if not org:
                msg = 'Organization %s not found' % self.oname
                self.module.fail_json(msg=msg)
            org_guid = org['metadata']['guid']
            space = self.cf.search_space(org_guid, self.name)
            if state == 'present':
                result = self.present(space, org_guid)
            elif state == 'absent':
                recursive = self.module.params['force']
                result = self.absent(space, org_guid, recursive)
            else:
                self.module.fail_json(msg='Invalid state: %s' % state)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))
        self.module.exit_json(**result)

    def absent(self, space, org_guid, recursive, async=False):
        changed = False
        if space is not None:
            space_guid = space['metadata']['guid']
            changed = True
            if not self.module.check_mode:
                try:
                    self.cf.delete_space(space_guid, async, recursive)
                except CFException as e:
                    msg = 'Cannot delete space %s: %s' % (self.name, str(e))
                    self.module.fail_json(msg=msg)
        result = {
            'changed': changed,
            'msg': "CF space %s deleted from %s org" % (self.name, self.oname)
        }
        return result

    def present(self, space, org_guid):
        # pre check to see if user exists
        user = None
        user_name = self.module.params['user_name']
        if user_name is not None:
            user = self.cf.search_user(user_name)
            if user is None:
                self.module.fail_json(msg="User %s not found" % (user_name))
        changed = False
        if space is None:
            changed = True
            if not self.module.check_mode:
                try:
                    space = self.cf.save_space(org_guid, self.name,
                        self.module.params['allow_ssh'])
                except CFException as e:
                    msg = "Cannot create space %s: %s" % (self.name, str(e))
                    self.module.fail_json(msg=msg)
            msg = "CF space %s created in %s org" % (self.name, self.oname)
        else:
            guid = space['metadata']['guid']
            space_items = ['name', 'allow_ssh']
            for item in space_items:
                if self.module.params[item] != space['entity'][item]:
                    changed = True
                    break
            if org_guid != space['entity']['organization_guid']:
                changed = True
            if changed:
                if not self.module.check_mode:
                    try:
                        space = self.cf.save_space(org_guid, self.name,
                            self.module.params['allow_ssh'], guid)
                    except CFException as e:
                        msg = "Cannot update space %s: %s" % (self.name, str(e))
                        self.module.fail_json(msg=msg)
                msg = "CF space %s in %s org updated" % (self.name, self.oname)
            else:
                msg = "CF space %s in %s org no update needed" % (self.name, self.oname)
        changed_user = False
        if user is not None:
            mode = self.module.params['user_state'] == "present"
            spc_uid = space['metadata']['guid']
            user_id = user['metadata']['guid']
            user_role = self.module.params['user_role']
            changed_user = self.cf.manage_space_users(spc_uid, user_id, user_role, mode)
        result = {
            'changed': changed or changed_user,
            'msg': msg,
            'data': space
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
            organization = dict(required=True, type='str'),
            allow_ssh = dict(required=False, default=False, type='bool'),
            user_name = dict(required=False, type='str'),
            user_role = dict(default='developer', type='str', choices=['developer', 'manager', 'auditor']),
            user_state = dict(default='present', type='str', choices=['present', 'absent']),
            force = dict(default=False, type='bool'),
        ),
        supports_check_mode = True
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_Space(module)
    cf.run()


if __name__ == '__main__':
    main()
