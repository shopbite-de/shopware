# syntax=docker/dockerfile:1
#
# Production image for the ShopBite Shopware 6 installation.
# Follows the official Shopware recipe (shopware/docker 0.3) and the hosting guide:
# https://developer.shopware.com/docs/guides/hosting/installation-updates/docker.html
#
#   docker build --pull -f docker/Dockerfile -t shopbite/shopware .
#
# Build secrets (both optional, only mounted when passed with --secret):
#   --secret id=packages_token,env=SHOPWARE_PACKAGES_TOKEN   # packages.shopware.com token
#   --secret id=composer_auth,src=auth.json                  # composer auth.json (private repos)

ARG PHP_VERSION=8.4

# FrankenPHP is the base recommended by Shopware for containers: one process, automatic resource allocation.
# Rolling tag on purpose: `docker build --pull` picks up the daily PHP/OS security rebuilds.
FROM ghcr.io/shopware/docker-base:${PHP_VERSION}-frankenphp AS base-image
FROM ghcr.io/shopware/shopware-cli:latest-php-${PHP_VERSION} AS shopware-cli

# ---------------------------------------------------------------------------
# Build stage: composer install (prod only), compile admin/storefront assets,
# assets:install, strip node_modules & sources, generate SBOM.
# ---------------------------------------------------------------------------
FROM shopware-cli AS build

COPY . /src
WORKDIR /src

RUN --mount=type=secret,id=packages_token,env=SHOPWARE_PACKAGES_TOKEN \
    --mount=type=secret,id=composer_auth,dst=/src/auth.json \
    --mount=type=cache,target=/root/.composer \
    --mount=type=cache,target=/root/.npm \
    /usr/local/bin/entrypoint.sh shopware-cli project ci /src

# ---------------------------------------------------------------------------
# Final image: FrankenPHP + Caddy serving /var/www/html/public on :8000.
# Runs as www-data (uid 82). Setup/updates run via `vendor/bin/shopware-deployment-helper run`.
# ---------------------------------------------------------------------------
FROM base-image AS final

ENV SHOPWARE_DISABLE_UPDATE_CHECK=1

# Base Caddyfile + long-lived Cache-Control for /media, /thumbnail, /bundles, /theme
COPY --link docker/Caddyfile /etc/caddy/Caddyfile

COPY --from=build --chown=82 --link /src /var/www/html
