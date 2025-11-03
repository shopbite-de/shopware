ARG PHP_VERSION=8.4
FROM ghcr.io/shopware/docker-base:$PHP_VERSION-caddy AS base-image
FROM ghcr.io/shopware/shopware-cli:latest-php-$PHP_VERSION AS shopware-cli

FROM shopware-cli AS build

ENV SHOPWARE_PACKAGES_TOKEN=SHOPWARE_PACKAGES_TOKEN

ADD . /src
WORKDIR /src

RUN --mount=type=secret,id=composer_auth,dst=/src/auth.json \
    --mount=type=cache,target=/root/.composer \
    --mount=type=cache,target=/root/.npm \
    /usr/local/bin/entrypoint.sh shopware-cli project ci /src

FROM base-image AS final

COPY docker/Caddyfile /etc/caddy/Caddyfile

COPY --from=build --chown=82 --link /src /var/www/html