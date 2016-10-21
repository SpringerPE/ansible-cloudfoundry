# Ansible Inventory

Ansible inventory files for the playbooks, load with the flag `-i inventory/<name>` from the playbook's folder.

Variables are defined under the `cfclient` key (see `test` inventory file and modify it according to your platform),
so it makes possible targeting different Cloud Foundry environments with the same playbooks.
