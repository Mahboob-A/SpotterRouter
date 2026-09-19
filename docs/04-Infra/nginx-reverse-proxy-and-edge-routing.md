# Nginx Reverse Proxy and Static Asset Architecture

## Overview

In production, SpotterRouter runs Nginx as an edge reverse proxy in front of the Python Gunicorn application server. This document explains where Nginx is placed, what responsibilities it handles, and why this design was chosen over exposing the Python server directly.

---

## Placement in the Architecture

The request flow in production is arranged in layers:

1. The client browser sends an HTTP or HTTPS request to the server.
2. An edge ingress (such as Traefik on a cloud host or direct firewall port forwarding) forwards the incoming connection to Nginx on port 80.
3. Nginx inspects the request path:
   - If the request path begins with `/static/`, Nginx reads the static asset directly from the local disk volume and returns it immediately.
   - For all other paths (UI pages, API endpoints, health checks), Nginx proxies the connection over the internal Docker network to Gunicorn running in the `backend` container on port 8000.
4. Gunicorn processes the request and sends the response back to Nginx, which streams it to the user.

---

## Why Use Nginx Instead of Direct Gunicorn?

Python application servers like Gunicorn are built to run Python WSGI code, not to serve static files or handle slow client connections. Putting Nginx in front provides three major advantages:

1. Fast Static Asset Delivery
   Django comes with static file finders for development, but in production running Python code to serve CSS, JavaScript, and favicon images wastes server CPU and memory. Nginx uses kernel-level zero-copy file transfer (`sendfile`) to deliver static files with minimal resource usage.

2. Buffering Slow Clients
   If a client on a slow mobile connection uploads a payload or downloads a large response, connecting directly to Gunicorn ties up a Python worker thread for several seconds. Nginx buffers incoming requests and outgoing responses in memory, letting Python workers finish their work in milliseconds and return to the worker pool.

3. Edge Security and Header Hardening
   Nginx injects standard security headers onto every response before sending it to the client:
   - `X-Content-Type-Options: nosniff`: Prevents browsers from MIME-sniffing away from the declared content type.
   - `X-Frame-Options: DENY`: Protects against clickjacking by preventing the site from being rendered inside third-party iframes.
   - `Referrer-Policy: same-origin`: Protects sensitive URL query parameters from leaking to external referrers.

---

## Static Files Volume Configuration

Static assets are collected at container build time:

1. The Docker build runs `python manage.py collectstatic --noinput`, which gathers all CSS, JavaScript, Leaflet maps assets, and favicon files into `/app/staticfiles/`.
2. In `docker-compose.prod.yml`, the `staticfiles` volume is mounted read-only into the Nginx container at `/usr/share/nginx/html/static/`.
3. Nginx serves these files with aggressive caching headers (`Cache-Control: public, max-age=31536000, immutable`), reducing repeat network trips for browsers.

---

## Development vs Production Tradeoff

In local development, Nginx is omitted from `docker-compose.dev.yml`. Instead, the `backend` container exposes port 8000 directly to the developer's laptop, and Django serves static files using its built-in staticfiles handler.

This tradeoff keeps local development lightweight and fast:
- Developers do not need to rebuild Nginx containers or run `collectstatic` every time they edit a CSS stylesheet or template.
- Live file reloading works automatically through Gunicorn reload flags and volume mounts.
- When running in production, Nginx is brought in via `docker-compose.prod.yml` to provide security, speed, and concurrency protection.
