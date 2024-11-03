# How tunnel a SSH connection?
Use Netcat with the SSH ProxyProtocol feature.
```
ssh -o "ProxyCommand=ncat --proxy-auth user:1234 --proxy-type socks5 --proxy 127.0.0.1:1080 %h %p" root@your.intercept.hostname.com
```


# Docker Compose example
```
services:
  ziti-edge-proxy:
    image: registry.dev.eriks.life/erikslife/containers/ziti-edge-proxy:main
    ports:
      - "1080:1080"
    environment:
      PROXY_HOST: 0.0.0.0
      PROXY_PORT: 1080
      PROXY_USERNAME: user
      PROXY_PASSWORD: 1234
      ZITI_IDENTITIES: /app/identity.json
    volumes:
      - "./identity.json:/app/identity.json"
```

Or simpler without volumes:
```
services:
  ziti-edge-proxy:
    image: registry.dev.eriks.life/erikslife/containers/ziti-edge-proxy:main
    ports:
      - "1080:1080"
    environment:
      PROXY_HOST: 0.0.0.0
      PROXY_PORT: 1080
      PROXY_USERNAME: user
      PROXY_PASSWORD: 1234
      ZITI_IDENTITY: "eyXXXXX" # Your identity.json just Base64 encoded, no JWT Token!
```