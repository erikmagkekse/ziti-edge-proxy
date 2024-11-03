# What is the ziti-edge-proxy?
This project uses OpenZiti to provide a SOCKS5 Proxy with simple authentication that tunnels intercepted traffic trough OpenZiti.
The goal for this project was to make it fully working in the UserSpace, so that it can be used also in Pipelines, as example for GitOps processes.

## For who is it for?
For everyone who needs a simple and fully in userspace solution for OpenZiti, very useful as example in pipelines.
As example you are a infrastructure guy who uses OpenZiti and uses Gitlab to rollout Ansible Playbooks, you know one curcial part is to secure your runners, as example from a Network perspective.
Many many runners just have to much network privileges in a infrastructure, and it makes it impossible to share a Runner with other Teams in a Company, now this can be solved with OpenZiti and ziti-edge-proxy!

## How can it be used?
Its simple! Either just try it out with Docker Compose or integrate it directly into your pipelines. 
Check out some examples:
- [Docker Compose](https://github.com/erikmagkekse/ziti-edge-proxy/tree/main/examples/docker-compose) 
- [Gitlab](https://github.com/erikmagkekse/ziti-edge-proxy/tree/main/examples/gitlab) 

### Docker Image
This container image will be monitored regularly to keep the current CVEs in the image minimal. Currently the tagging of the images is solved by the branch name, "main" is the stable branch.
```
docker pull docker.io/erikmagkekse/ziti-edge-proxy:main
```
[DockerHub](https://hub.docker.com/erikmagkekse/ziti-edge-proxy/)

### Enviroment variables
| Variable        | Default Value           | Usage  |
| ------------- |:-------------:| -----:|
| PROXY_HOST | 127.0.0.1 | Where the SOCKS5 server should be attached too |
| PROXY_PORT | 1080 | Default port of the SOCKS5 server |
| PROXY_USERNAME | user | Username for the SOCKS5 server |
| PROXY_PASSWORD | password | Password of the SOCKS5 Server |
| *ZITI_IDENTITES | *empty* | List of used Ziti identities, seperated by simicolon |
| *ZITI_IDENTITY | *empty* | A Base64 encoded string of a single identity json |

\*Only one of them can be used at a time and is not optional, if you use ZITI_IDENTITY it will decode the identity json to "/app/identity.json" and updates the var ZITI_IDENTITIES to the file.


## Future plans
- Switch from Python image to Alpine or RedHat UBI
- Add HTTP Proxy support
- Rewrite in Go

## Note
This project is not beeing developed by NetFoundry or OpenZiti itself, it only uses the SDKs of OpenZiti.
