# How tunnel a SSH connection?
Use Netcat with the SSH ProxyProtocol feature.
```
ssh -o "ProxyCommand=ncat --proxy-auth user:1234 --proxy-type socks5 --proxy 127.0.0.1:1080 %h %p" root@your.intercept.hostname.com
```

Simple curl to use the HTTP Proxy as example.
```
curl -X http://127.0.0.1:8080 https://your.intercept.hostname.com
```


# Docker Compose example
```
services:
  ziti-edge-proxy:
    image: docker.io/erikmagkekse/ziti-edge-proxy:main
    ports:
      - "1080:1080"
    environment:
      PROXY_HOST: 0.0.0.0
      SOCKS_PORT: 1080
      HTTP_PORT: 8080
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
    image: docker.io/erikmagkekse/ziti-edge-proxy:main
    ports:
      - "1080:1080"
    environment:
      PROXY_HOST: 0.0.0.0
      SOCKS_PORT: 1080
      HTTP_PORT: 8080
      PROXY_USERNAME: user
      PROXY_PASSWORD: 1234
      ZITI_IDENTITY: "eyXXXXX" # Your identity.json just Base64 encoded, no JWT Token!
```