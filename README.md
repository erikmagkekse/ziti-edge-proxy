# What is the ziti-edge-proxy?
This project uses OpenZiti to provide a SOCKS5 Proxy with simple authentication that tunnels intercepted traffic trough OpenZiti.
The goal for this project was to make it fully working in the UserSpace, so that it can be used also in Pipelines, as example for GitOps processes.

## For who is it for?
For everyone who needs a simple and fully in UserSpace solution for OpenZiti, very useful as example in Pipelines.
As example you are a Infrastructure Guy who uses OpenZiti and uses Gitlab to rollout Ansible Playbooks, you know one curcial part is to secure your Runners, as example from a Network perspective.
Many many Runners just have to much Network Privileges in a Infrastructure, and it makes it impossible to share a Runner with other Teams in a Company, now this can be solved with OpenZiti and ziti-edge-proxy!

## How can it be used?
Its simple! Either just try it out with Docker Compose or integrate it directly into your Gitlab pipelines. 
More examples will follow!

## Future plans
1. Rewrite in Go
2. Add HTTP Proxy support
