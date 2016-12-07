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


__program__ = "cf_domain"
__version__ = "0.1.1"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"

DOCUMENTATION = '''
---
module: cf_domain
short_description: Manage Cloud Foundry Domains
description:
    - Manage Cloud Foundry Domains
author: "Jose Riguera, jose.riguera@springer.com"
options:
    state:
        description:
            - Desired state of the domain
        required: false
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the domain
        required: true
        default: null
        aliases: [id]
    type:
        description:
            - Domain type
        required: false
        default: shared
        choices: [shared, private]
    owner_organization:
        description:
            - Owner organization for private domains
        required: true (if type is private)
    shared_organization:
        description:
            - Share private domain with the organization
        required: false
    shared_state:
        description:
            - Desired state of the private domain with the shared_organization
        required: false
        default: present
        choices: [present, absent]
    router_group_guid:
        description:
            - Shared domain router_group_guid
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
            - Force deletion of system org and recursive entities in an org
        required: false
        default: false
'''

EXAMPLES = '''
- name: create shared domain testdomain.test.cf.example.com
  cf_domain:
    name: "testdomain.test.cf.example.com"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: create private domain ptestdomain.test.cf.example.com for test org
  cf_domain:
    name: "ptestdomain.test.cf.example.com"
    type: private
    owner_organization: "test"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"

- name: share domain ptestdomain.test.cf.example.com owned by test org with test2 org
  cf_domain:
    name: "ptestdomain.test.cf.example.com"
    type: private
    shared_organization: "test2"
    admin_user: "admin"
    admin_password: "password"
    api_url: "https://api.test.cf.example.com"
'''

RETURN = '''
...
'''


class CF_Domain(object):

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
        self.kind = self.module.params['type']

    def run(self):
        state = self.module.params['state']
        try:
            domain = self.cf.search_domain(self.name, self.kind)
            if state == 'present':
                shared_state = self.module.params['shared_state']
                mode = True if shared_state == "present" else False
                owner_org_guid = None
                if self.kind == "private":
                    if self.module.params['owner_organization'] is not None:
                        owner_org_name = self.module.params['owner_organization']
                        owner_org = self.cf.search_org(owner_org_name)
                        if not owner_org:
                            msg = 'Organization %s not found' % owner_org_name
                            self.module.fail_json(msg=msg)
                        owner_org_guid = owner_org['metadata']['guid']
                    else:
                        if domain is None:
                            # It cannot a not existing private domain if owner org
                            # is not provided
                            self.module.fail_json(msg='No domain found and organization is unknown!')
                shared_org_guid = None
                if self.module.params['shared_organization'] is not None:
                    shared_org_name = self.module.params['shared_organization']
                    shared_org = self.cf.search_org(shared_org_name)
                    if not shared_org:
                        msg = 'Organization to share domain to %s not found' % shared_org_name
                        self.module.fail_json(msg=msg)
                    shared_org_guid = shared_org['metadata']['guid']
                result = self.present(domain, owner_org_guid, shared_org_guid, mode)
            elif state == 'absent':
                result = self.absent(domain)
            else:
                self.module.fail_json(msg='Invalid state: %s' % state)
        except CFException as e:
            self.module.fail_json(msg=str(e))
        except Exception as e:
            self.module.fail_json(msg="Exception: %s" % str(e))
        self.module.exit_json(**result)

    def absent(self, domain, async=False):
        changed = False
        if domain is not None:
            domain_guid = domain['metadata']['guid']
            changed = True
            if not self.module.check_mode:
                try:
                    self.cf.delete_domain(domain_guid, self.kind, async)
                except CFException as e:
                    msg = 'Cannot delete domain %s: %s' % (self.name, str(e))
                    self.module.fail_json(msg=msg)
        result = {
            'changed': changed,
            'msg': "CF %s domain %s deleted" % (self.kind, self.name)
        }
        return result

    def present(self, domain, owner_org_guid, shared_org_guid, mode):
        changed = False
        if domain is None:
            changed = True
            if not self.module.check_mode:
                try:
                    if owner_org_guid is not None:
                        domain = self.cf.create_private_domain(self.name, owner_org_guid)
                    else:
                        domain = self.cf.create_shared_domain(self.name,
                            self.module.params['router_group_guid'])
                except CFException as e:
                    msg = 'Cannot create %s domain %s: %s' % (self.kind, self.name, str(e))
                    self.module.fail_json(msg=msg)
            msg = "CF %s domain %s created" % (self.kind, self.name)
        else:
            # No way to update domains
            msg = "CF %s domain %s exists" % (self.kind, self.name)
        changed_priv_org = False
        if shared_org_guid is not None:
            # private domain shared with other orgs
            domain_guid = domain['metadata']['guid']
            try:
                changed_priv_org = self.cf.manage_private_domain_organization(
                    domain_guid, shared_org_guid, mode)
            except CFException as e:
                msg = 'Cannot update %s domain %s: %s' % (self.kind, self.name, str(e))
                self.module.fail_json(msg=msg)
            if changed_priv_org:
                msg = msg + ", updated private domain shared organizations"
            else:
                msg = msg + ", no private domain shared organizations updated"
        result = {
            'changed': changed or changed_priv_org,
            'msg': msg,
            'data': domain
        }
        return result


def main():
    # http://mobygeek.net/blog/2016/02/16/ansible-module-development-parameters/
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='present', type='str', choices=['present', 'absent']),
            name = dict(required=True, type='str', aliases=['id']),
            admin_user = dict(required=True, type='str'),
            admin_password = dict(required=True, type='str', no_log=True),
            api_url = dict(required=True, type='str'),
            type = dict(default='shared', type='str', choices=['shared', 'private']),
            owner_organization = dict(required=False, type='str'),
            shared_organization = dict(required=False, type='str'),
            shared_state = dict(default='present', type='str', choices=['present', 'absent']),
            router_group_guid = dict(required=False, type='str'),
            force = dict(default=False, type='bool'),
        ),
        supports_check_mode = True,
        mutually_exclusive = [
            ['router_group_guid', 'owner_organization']
        ]
    )

    if not cfconfigurator_found:
        module.fail_json(msg="The Python module 'cfconfigurator' must be installed.")

    cf = CF_Domain(module)
    cf.run()


if __name__ == '__main__':
    main()
