# ziti-edge-proxy | ZeroTrust your Pipelines!
This project uses OpenZiti to provides a SOCKS5 & HTTP Proxy with simple authentication that tunnels intercepted traffic through OpenZiti.
The goal for this project was to make it fully functional in UserSpace, so that it can also be used in pipelines without privileges, for example in GitOps processes.

# Who is it for? The Shared Runner Problem!
Traditional CI/CD runners have a fundamental security flaw: **they need network access to your infrastructure**.

```
┌─────────────────────────────────────────────────────────┐
│                    GitLab / GitHub                      │
├─────────────────────────────────────────────────────────┤
│   Team A          Team B          Team C                │
│   (Finance)       (DevOps)        (Marketing)           │
│      │               │               │                  │
│      └───────────────┼───────────────┘                  │
│                      ▼                                  │
│              ┌────────────────┐                         │
│              │ SHARED RUNNER  │                         │
│              │  (has broad    │                         │
│              │ network access)│                         │
│              └───────┬────────┘                         │
│                      │                                  │
│                      ▼                                  │
│         Your entire network is exposed 😱               │
└─────────────────────────────────────────────────────────┘
```

**This creates serious risks:**

| Risk | Impact |
|------|--------|
| **Lateral Movement** | Team A's pipeline can reach Team B's servers |
| **Credential Exposure** | Compromised job sees your whole network |
| **Blast Radius** | Runner hacked = everything reachable |

## Why Not Use the Official OpenZiti Tunneler?

OpenZiti's official tunnelers (`ziti-edge-tunnel`) require:
- Root/privileged mode
- TUN device (`/dev/net/tun`)
- Kernel-level network manipulation

**This doesn't work in:**
- Unprivileged CI/CD runners
- Kubernetes pods without `privileged: true`
- Serverless / Container-as-a-Service platforms

## The Solution

**ziti-edge-proxy** takes a different approach:

```
Instead of:  Traffic ──► TUN Device ──► Kernel ──► Ziti
                         (requires root)

We do:       Traffic ──► SOCKS5/HTTP Proxy ──► Ziti SDK (UserSpace)
                         (requires nothing)
```

## Architecture with ziti-edge-proxy

```
┌─────────────────────────────────────────────────────────┐
│                    GitLab / GitHub                      │
├─────────────────────────────────────────────────────────┤
│   Team A              Team B              Team C        │
│      │                   │                   │          │
│      ▼                   ▼                   ▼          │
│ ┌─────────┐        ┌─────────┐        ┌─────────┐       │
│ │ Identity│        │ Identity│        │ Identity│       │
│ │ Team-A  │        │ Team-B  │        │ Team-C  │       │
│ └────┬────┘        └────┬────┘        └────┬────┘       │
│      └──────────────────┼───────────────────┘           │
│                         ▼                               │
│                ┌────────────────┐                       │
│                │ SHARED RUNNER  │                       │
│                │ (NO network    │                       │
│                │  access!)      │                       │
│                └───────┬────────┘                       │
│                        │ localhost only                 │
│                        ▼                                │
│               ┌─────────────────┐                       │
│               │ ziti-edge-proxy │                       │
│               │ + Team Identity │                       │
│               └────────┬────────┘                       │
└────────────────────────┼────────────────────────────────┘
                         │ OpenZiti Overlay (encrypted)
                         ▼
           ┌─────────────────────────────────────┐
           │         Your Network                │
           │                                     │
           │  Team A servers   Team B servers    │
           │  (only reachable  (only reachable   │
           │   by Team A        by Team B        │
           │   Identity)        Identity)        │
           └─────────────────────────────────────┘
```

## The Key Difference

**One shared runner, but each pipeline only sees what it needs.**

| Aspect | Traditional | With ziti-edge-proxy |
|--------|-------------|----------------------|
| **Firewall** | Ports open for runner IPs | No inbound ports needed |
| **Privileges** | Runner needs network access | Only localhost proxy |
| **Isolation** | Runner sees entire network | Runner sees only authorized services |
| **Shared Runners** | Security nightmare | Zero Trust by design |
| **Root required** | Yes (for tunnelers) | No (pure userspace) |

# How can i use it?
It's simple! You can either try it out with Docker Compose or integrate it directly into your pipelines.
Check out some examples:
- [GitHub](https://github.com/erikmagkekse/ziti-edge-proxy/tree/main/examples/github)
- [GitLab](https://github.com/erikmagkekse/ziti-edge-proxy/tree/main/examples/gitlab)
- [Docker Compose](https://github.com/erikmagkekse/ziti-edge-proxy/tree/main/examples/docker-compose)

## Docker Image
This container image will be monitored regularly, as soon as we are in beta state, to keep the current CVEs in the image minimal. Currently, the tagging of the images is based on the branch name, "main" is the stable branch.
```
docker pull ghcr.io/erikmagkekse/ziti-edge-proxy:main
```
[GitHub Container Registry](https://github.com/erikmagkekse/ziti-edge-proxy/pkgs/container/ziti-edge-proxy)

## Environment variables
| Variable         | Default Value     | Usage                                                                                |
| ---------------- | ----------------- | ------------------------------------------------------------------------------------ |
| PROXY_HOST       | 127.0.0.1         | Where the SOCKS5 server should be attached                                           |
| SOCKS_ENABLED    | true              | Enables SOCKS5 Server                                                                |
| HTTP_ENABLED     | true              | Enables HTTP Server                                                                  |
| SOCKS_PORT       | 1080              | Default port of the SOCKS5 server                                                    |
| HTTP_PORT        | 8080              | Default port of the HTTP proxy server                                                |
| PROXY_USERNAME   | user              | Username for the SOCKS5 server                                                       |
| PROXY_PASSWORD   | password          | Password for the SOCKS5 Server                                                       |
| *ZITI_IDENTITIES | *empty*           | List of used Ziti identities, separated by semicolon, can be also a wildcard.        |
| *ZITI_IDENTITY   | *empty*           | A Base64 encoded string of a single identity JSON                                    |

\*Only one of these can be used at a time and is not optional. If you use ZITI_IDENTITY, it will decode the identity JSON to "/app/identity.json" and update the var ZITI_IDENTITIES to point to the file.

## Future roadmap
- Add Codesinging
- Improving logging ✅
- Add ghcr.io repository for image ✅
- Switch from Python image to Alpine or RedHat UBI
- Add HTTP Proxy support ✅
- Rewrite in Go
- CI Tests

# FAQ
**Q: Is this slower than the official tunneler?**  
A: Yes, userspace proxying has some overhead. For CI/CD pipelines, this is negligible. For high-throughput production use, consider the official tunneler.

**Q: What if my tool doesn't support proxy settings?**  
A: Most tools support `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` environment variables. For tools that don't, consider using `proxychains` or similar.

**Q: Can I use multiple identities?**  
A: Yes! Use `ZITI_IDENTITIES` with semicolon-separated paths or wildcards like `/identities/*.json`.


# Note
This **project is NOT developed by NetFoundry or OpenZiti** itself, it only uses the SDKs of OpenZiti.

# Contributing
Contributions welcome! Please feel free to submit issues and pull requests.

