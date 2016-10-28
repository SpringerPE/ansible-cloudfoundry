# ansible-modules-cloudfoundry

Set of Ansible modules to manage Cloud Foundry configuration entities,
not aimed to manage apps, routes, service brokers, etc.

Current available modules make possible to manage:

* **cf_config**: Environment variables, feature flags and default security groups.
* **cf_domain**: Private (with owner/shared organizations) and shared domains
* **cf_org**: Organizations (and user roles: user, manager, auditor and billing_manager)
* **cf_space**: Spaces (and user roles: user, manager, auditor)
* **cf_quota**: Organization and space Quotas
* **cf_secgroup**: Security groups
* **cf_secgroup_rule**: Security group rules
* **cf_user**: Manage CF users via UAA

They depend on https://github.com/SpringerPE/python-cfconfigurator ,
just install it via pip.

```
pip install -r requirements.txt
```

For examples, have a look at `examples` folder.


## TODO

Buildpack management


## Author

José Riguera López, jose.riguera@springer-sbm.com

SpringerNature Platform Engineering
