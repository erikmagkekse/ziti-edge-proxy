# Github Actions example with ziti-edge-proxy
Note: For some reason the GitHub runners have something on port 8080 already listening, the port of this example got changed because of that to 7070.
Also make sure to use 127.0.0.1, Github will expose the service containers to localhost.
Don't forget to create a secret in Guthub with the Base64 encoded Ziti Identity called ZITI_IDENTITY.