# Ansible Inventory

Ansible inventory files for the playbooks, load them with the flag
`-i inventory/<name>` from the playbook's folder.

Each inventory files needs a root key called `cf` (see `cf.yml`
playbook in the root folder). Each of the children components of
the `cf` key represents a CF environment. In order to apply the same
settings to more than one environment, just define more children
entries, when the playbook run, it will automatically execute the
the settings on each enviroment (`serial: 1`)

It makes possible targeting different Cloud Foundry environments
with the same variables defined in group_vars: orgs, users, security
groups, ...

In order to define the orgs, spaces, users, environment variables ...
for different environments, just create a new yml/json file inside
the folder `group_vars` with the same name you used in the inventory.
