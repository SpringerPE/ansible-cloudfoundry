# ansible-cloudfoundry

Set of Ansible modules to manage Cloud Foundry configuration entities,
not aimed to manage apps, routes, service brokers, etc.

Current available modules make possible to manage:

* **cf_config**: Environment variables, feature flags and default security groups. 
* **cf_domain**: Private (with owner/shared organizations) and shared domains
* **cf_org**: Organizations
* **cf_space**: Spaces
* **cf_quota**: Organization and space Quotas
* **cf_secgroup**: Security groups
* **cf_secgroup_rule**: Security group rules

They depend on https://github.com/SpringerPE/python-cfconfigurator ,
just install it via pip.

```
pip install -r requirements.txt
```

For usage examples, have a look at `examples` folder.


## Author

José Riguera López, jose.riguera@springer-sbm.com

SpringerNature Platform Engineering
