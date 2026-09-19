# Dokploy Platform Deployment and Traefik Ingress

## Overview

Dokploy is a lightweight, open-source deployment platform designed for hosting Docker applications on a self-managed Linux virtual private server (VPS). It provides git-based deployments, automatic SSL certificates, and environment variable management through an intuitive web interface.

This document details how SpotterRouter deploys to Dokploy and integrates with Traefik edge routing.

---

## Deployment Architecture on Dokploy

When deploying SpotterRouter to a Dokploy VPS:

1. Dokploy clones the git repository and checks out the designated branch.
2. Dokploy runs the production multi-stage build using `docker-compose.prod.yml`.
3. The resulting container stack attaches to Dokploy's pre-configured external network, named `dokploy-network`.
4. Dokploy's internal Traefik ingress controller detects the newly launched containers and begins proxying web traffic to the application.

---

## Integrating with the Dokploy Network

Dokploy isolates applications using a dedicated Docker network. For Traefik to route public requests to the application container, the service must join this network.

In `docker-compose.prod.yml`:

```yaml
networks:
  default:
    name: spotter-network
  dokploy-network:
    external: true
```

The `backend` container is attached to both `spotter-network` (to talk to PostgreSQL, Redis, and OSRM internally) and `dokploy-network` (to receive HTTP requests from Traefik).

---

## Dynamic Port Mapping and Ingress Routing

In Dokploy, external edge routing is managed by Traefik. The platform expects the web container to listen on an internal port (typically 8000), which Traefik forwards to domain names configured in the Dokploy dashboard.

Key configuration rules:
- Internal Port: Set to `8000` in the Dokploy UI container settings.
- Domain Configuration: The domain (such as `spotterrouter.com`) points via DNS A/AAAA records to the VPS public IP address.
- SSL Certificates: Traefik automatically requests and renews valid HTTPS certificates from Let's Encrypt using the HTTP-01 challenge.

---

## Container Restart Policy

All production services configure `restart: unless-stopped`:

- If the server reboots for operating system patches, Docker brings the application stack back online automatically.
- If a container experiences an out-of-memory event or transient crash, Docker restarts the container without manual intervention.

---

## Zero Port Conflicts

Because services communicate through Traefik and Docker networks:
- Production does not bind ports 5432 (database) or 6379 (Redis) to the host public IP.
- Multiple applications can coexist on the same Dokploy VPS without port collisions.
- Only port 80 and port 443 are exposed to the open internet through Traefik.
