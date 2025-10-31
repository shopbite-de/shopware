# pin versions
FROM ghcr.io/shopware/docker-base:8.4 as base-image
FROM ghcr.io/friendsofshopware/shopware-cli:latest-php-8.4 as shopware-cli

# build

FROM shopware-cli as build

COPY --link . /src
WORKDIR /src

RUN --mount=type=secret,id=composer_auth,dst=/src/auth.json \
    --mount=type=cache,target=/root/.composer \
    --mount=type=cache,target=/root/.npm \
    /usr/local/bin/entrypoint.sh shopware-cli project ci /src

# build final image

FROM base-image

USER root

RUN apk add --no-cache shadow && \
    usermod -u 1000 www-data && \
    groupmod -g 1000 www-data

USER www-data

COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=build --chown=www-data:www-data /src /var/www/html
