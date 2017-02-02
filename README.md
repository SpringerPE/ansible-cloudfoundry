# ansible-cloudfoundry

Cloud Foundry resource automation using Ansible

Have a look at the repository with the role:
https://github.com/SpringerPE/ansible-cloudfoundry-role/
to see how to define the resources: feature flags, domains, security groups, quotas,
environment variables, users, organizations and spaces.

Install the role with ansible-galaxy by typing:

```
ansible-galaxy install -p ./roles -r requirements.yml
```

You can manage different Cloud Foundry environments by using inventory
files like this one: `inventory/cf.ini`
It makes possible to define some common global configuration variables by splitting
them in different files (Ansible superpower!)

Once the CF credentials are defined in the inventory and the resources in the manifest,
just run ansible:

```
ansible-playbook -i inventory/cf.ini cf.yml
```

and done!


# Components

### `roles`

Ansible roles to use in the playbooks.


### `inventory`

Folder with the variables needed to set-up on each CF environment.
Have a look at the [Readme in the folder](https://github.com/SpringerPE/ansible-cloudfoundry/blob/master/inventory/Readme.md), to see how to operate.


### `cf.yml`

Ansible playbook to run.

```
ansible-playbook -i inventory/test.ini cf.yml
```



## Author

José Riguera López, jose.riguera@springer-sbm.com

SpringerNature Platform Engineering

Copyright 2017 Springer Nature
