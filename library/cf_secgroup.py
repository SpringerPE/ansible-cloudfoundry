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


__program__ = "cf_secgroup"
__version__ = "0.1.1"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_secgroup
short_description: Manage Cloud Foundry Security groups
description:
    - Manage Cloud Foundry Security groups
author: "Jose Riguera, jose.riguera@springer.com"
options:
    state:
        description:
            - Desired state of the Security Group
        required: false
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the security group
        required: true
        default: null
        aliases: [id]
    organization:
        description:
            - Organization to setup space quota
        required: true if space, otherwise false
    space:
        description:
            - Space to setup space quota
        required: true if organization, otherwise false
    space_state:
        description:
            - Desired state of the Security Group in the Org/Space
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
            - Force deletion of (system) entities
        required: false
        default: false
'''

EXAMPLES = '''
- name: create test-secgroup
  cf_secgroup:
    name: "test-secgroup"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: create test-secgroup link with test org test space
  cf_secgroup:
    name: "test-secgroup"
    space: "test"
    organization: "test"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: delete test-secgroup
  cf_secgroup:
    name: "test-secgroup"
    state: absent
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
'''

RETURN = '''
...
'''


class CF_Secgroup(object):

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
        try:
            sec_group = self.cf.search_secgroup(self.name)
            if state == 'present':
                space_state = self.module.params['space_state']
                mode = True if space_state == "present" else False
                space_guid = None
                if self.module.params['organization'] is not None:
                    org = self.cf.search_org(self.module.params['organization'])
                    if not org:
                        self.module.fail_json(msg='Organization not found')
                    org_guid = org['metadata']['guid']
                    space_name = self.module.params['space']
                    space = self.cf.search_space(org_guid, space_name)
                    if not space:
                        self.module.fail_json(msg='Space not found')
                    space_guid = space['metadata']['guid']
                result = self.present(sec_group, space_guid, mode)
            elif state == 'absent':
                result = self.absent(sec_group)
            else:
                self.module.fail_json(msg='Invalid state: %s' % state)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))
        self.module.exit_json(**result)

    def absent(self, sec_group, async=False):
        changed = False
        if sec_group is not None:
            sec_group_guid = sec_group['metadata']['guid']
            changed = True
            if not self.module.check_mode:
                try:
                    self.cf.delete_secgroup(sec_group_guid, async)
                except CFException as e:
                    msg = 'Cannot delete security group %s: %s' % (self.name, str(e))
                    self.module.fail_json(msg=msg)
        result = {
            'changed': changed,
            'msg': "CF security group %s deleted" % (self.name)
        }
        return result

    def present(self, sec_group, space_guid, mode):
        changed = False
        if sec_group is None:
            changed = True
            if not self.module.check_mode:
                try:
                    sec_group = self.cf.save_secgroup(self.name)
                except CFException as e:
                    msg = "Cannot create security group %s: %s" % (self.name, str(e))
                    self.module.fail_json(msg=msg)
            msg = "CF security group %s created" % (self.name)
        else:
            # No way to update sec group
            msg = "CF security group %s exists" % (self.name)
        changed_spaces = False
        if space_guid is not None:
            # space in/out secgroup
            sec_group_guid = sec_group['metadata']['guid']
            try:
                changed_spaces = self.cf.manage_secgroup_space(sec_group_guid, space_guid, mode)
            except Exception as e:
                msg = 'Cannot update %s sec group with space %s: %s' % (self.name, space_guid, str(e))
                self.module.fail_json(msg=msg)
            if changed_spaces:
                msg = msg + ", updated security group spaces"
            else:
                msg = msg + ", no updated security group spaces"
        result = {
            'changed': changed or changed_spaces,
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
            organization = dict(required=False, type='str'),
            space = dict(required=False, type='str'),
            space_state = dict(default='present', type='str', choices=['present', 'absent']),
            force = dict(default=False, type='bool'),
        ),
        supports_check_mode = True,
        required_together = [
            ['organization', 'space']
        ]
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_Secgroup(module)
    cf.run()


if __name__ == '__main__':
    main()
