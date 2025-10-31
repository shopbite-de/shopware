FROM ghcr.io/shopware/docker-dev:php8.4-node24-caddy

COPY --chown=www-data:www-data --link . /var/www/html

COPY docker/Caddyfile /etc/caddy/Caddyfile
