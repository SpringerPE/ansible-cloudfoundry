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


__program__ = "cf_org"
__version__ = "0.1.1"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_org
short_description: Manage Cloud Foundry Orgs
description:
    - Manage Cloud Foundry Orgs
author: "Jose Riguera, jose.riguera@springer.com"
options:
    state:
        description:
            - Desired state of the org
        required: false
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the org
        required: true
        default: null
        aliases: [id]
    quota:
        description:
            - Name of the quota asigned to the org
        required: false
        default: "default"
    user_name:
        description:
            - Name of the user to add/remove to the org
        required: false
    user_role:
        description:
            - Role of the user in the org
        required: false
        default: "user"
        choices=[user, manager, auditor, billing_manager]
    user_state:
        description:
            - Desired state of the org
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
            - Force deletion of system org and recursive entities in an org
        required: false
        default: false
'''

EXAMPLES = '''
- name: create org test with default quotas
  cf_org:
    name: "test"
    quota: "default"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

# Warning! In order to add an user as [manager, auditor, billing_manager]
# first they have to be added as a user!, otherwise the error:
# CF-InvalidRelation (1002) will appear

- name: create/update org test with bob as user
  cf_org:
    name: "test"
    user_name: "bob"
    user_role: user
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: promote bob as manager in the test org
  cf_org:
    name: "test"
    user_name: "bob"
    user_role: manager
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: demote bob as user in the test org (still he is an user)
  cf_org:
    name: "test"
    user_name: "bob"
    user_role: manager
    user_state: absent
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
'''

RETURN = '''
...
'''


class CF_Org(object):
    system_orgs = ['pivotal']

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
            org = self.cf.search_org(self.name)
            if state == 'present':
                quota_name = self.module.params['quota']
                result = self.present(org, quota_name)
            elif state == 'absent':
                if self.name in self.system_orgs and not force:
                    self.module.fail_json(msg="Cannot delete a system org")
                result = self.absent(org, force)
            else:
                self.module.fail_json(msg='Invalid state: %s' % state)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))
        self.module.exit_json(**result)

    def absent(self, org, recursive, async=False):
        changed = False
        if org is not None:
            org_guid = org['metadata']['guid']
            changed = True
            if not self.module.check_mode:
                try:
                    self.cf.delete_org(org_guid, async, recursive)
                except CFException as e:
                    msg = 'Cannot delete org %s: %s' % (self.name, str(e))
                    self.module.fail_json(msg=msg)
        result = {
            'changed': changed,
            'msg': "CF org %s deleted" % self.name
        }
        return result

    def present(self, org, quota_name):
        # pre check to see if user exists
        user = None
        user_name = self.module.params['user_name']
        if user_name is not None:
            user = self.cf.search_user(user_name)
            if user is None:
                self.module.fail_json(msg="User %s not found" % (user_name))
        changed = False
        if org is None:
            if quota_name is None:
                quota_name = 'default'
            quota = self.cf.search_quota(quota_name)
            if not quota:
                self.module.fail_json(msg="Quota %s not found" % quota_name)
            quota_guid = quota['metadata']['guid']
            changed = True
            if not self.module.check_mode:
                try:
                    org = self.cf.save_org(self.name, quota_guid)
                except CFException as e:
                    msg = "Cannot create org %s: %s" % (self.name, str(e))
                    self.module.fail_json(msg=msg)
            msg = "CF org %s created" % self.name
        else:
            if quota_name is None:
                quota_guid = None
            else:
                quota = self.cf.search_quota(quota_name)
                if not quota:
                    self.module.fail_json(msg="Quota %s not found" % quota_name)
                quota_guid = quota['metadata']['guid']
            guid = org['metadata']['guid']
            if quota_guid is not None and org['entity']['quota_definition_guid'] != quota_guid:
                changed = True
                if not self.module.check_mode:
                    try:
                        org = self.cf.save_org(self.name, quota_guid, guid)
                    except CFException as e:
                        msg = "Cannot update org %s: %s" % (self.name, str(e))
                        self.module.fail_json(msg=msg)
                msg = "CF org %s updated" % self.name
            else:
                msg = "CF org %s not updated" % self.name
        changed_user = False
        if user is not None:
            mode = self.module.params['user_state'] == "present"
            org_uid = org['metadata']['guid']
            user_id = user['metadata']['guid']
            user_role = self.module.params['user_role']
            changed_user = self.cf.manage_organization_users(org_uid, user_id, user_role, mode)
        result = {
            'changed': changed or changed_user,
            'msg': msg,
            'data': org
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
            quota = dict(type='str'),
            user_name = dict(required=False, type='str'),
            user_role = dict(default='user', type='str', choices=['user', 'manager', 'auditor', 'billing_manager']),
            user_state = dict(default='present', type='str', choices=['present', 'absent']),
            validate_certs = dict(default=False, type='bool'),
            force = dict(default=False, type='bool'),
        ),
        supports_check_mode = True,
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_Org(module)
    cf.run()


if __name__ == '__main__':
    main()
