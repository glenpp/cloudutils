# cloudutils
Various utilities relating to Cloud and automation

aws_sync_keys.py - merges/syncs ssh Ids of AWS EC2 instances with ~/.ssh/known_hosts to ensure there's no MiM. Could be run as an automation task after provisioning instances.
For full detail see https://www.pitt-pladdy.com/blog/_20160717-152327_0100_AWS_ssh_known_host_sync/

kube2haproxy.py - External Load Balancer configuration glue script for Kubernetes. This looks at services available via NodePort and appends the appropriate config to a template for HA Proxy to do the load balancing. For full detail see https://www.pitt-pladdy.com/blog/_20170328-130720_0100_Kubernetes_to_learn_Part_4/

