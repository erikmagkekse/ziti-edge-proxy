# What is ziti-edge-proxy?
This project uses OpenZiti to provide a SOCKS5 Proxy with simple authentication that tunnels intercepted traffic through OpenZiti.
The goal for this project was to make it fully functional in UserSpace, so that it can also be used in pipelines without privileges, for example in GitOps processes.

## Who is it for?
It’s for anyone who needs a simple and fully in-UserSpace solution for OpenZiti, which is especially useful in pipelines.
For example, if you are an infrastructure professional who uses OpenZiti and GitLab to roll out Ansible Playbooks, you know how crucial it is to secure your runners, for instance from a network perspective.
Many runners have too many network privileges within an infrastructure, making it impossible to share a runner with other teams in a company. Now, this can be addressed with OpenZiti and ziti-edge-proxy!

## How can it be used?
It's simple! You can either try it out with Docker Compose or integrate it directly into your pipelines.
Check out some examples:
- [Docker Compose](https://github.com/erikmagkekse/ziti-edge-proxy/tree/main/examples/docker-compose)
- [GitLab](https://github.com/erikmagkekse/ziti-edge-proxy/tree/main/examples/gitlab)

### Docker Image
This container image will be monitored regularly, as soon as we are in beta state, to keep the current CVEs in the image minimal. Currently, the tagging of the images is based on the branch name, "main" is the stable branch.
```
docker pull docker.io/erikmagkekse/ziti-edge-proxy:main
```
[DockerHub](https://hub.docker.com/r/erikmagkekse/ziti-edge-proxy)

### Environment variables
| Variable         | Default Value     | Usage                                                       |
| ---------------- | ----------------- | ----------------------------------------------------------- |
| PROXY_HOST       | 127.0.0.1         | Where the SOCKS5 server should be attached                  |
| PROXY_PORT       | 1080              | Default port of the SOCKS5 server                           |
| PROXY_USERNAME   | user              | Username for the SOCKS5 server                              |
| PROXY_PASSWORD   | password          | Password for the SOCKS5 Server                              |
| *ZITI_IDENTITIES | *empty*           | List of used Ziti identities, separated by semicolon        |
| *ZITI_IDENTITY   | *empty*           | A Base64 encoded string of a single identity JSON           |

\*Only one of these can be used at a time and is not optional. If you use ZITI_IDENTITY, it will decode the identity JSON to "/app/identity.json" and update the var ZITI_IDENTITIES to point to the file.

## Future roadmap
- Add Codesinging
- Improving logging
- Add ghcr.io repository for image
- Switch from Python image to Alpine or RedHat UBI
- Add HTTP Proxy support
- Rewrite in Go
- CI Tests

## Note
This project is NOT developed by NetFoundry or OpenZiti itself, it only uses the SDKs of OpenZiti.
