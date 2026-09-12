# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Shopware 6 installation** used for developing and running the `shopbite-de/shopware-plugin`. The repository itself is the Shopware project container — the plugin is managed as a Composer dependency (`vendor/shopbite-de/shopware-plugin/`). Changes to the plugin source are tracked via `composer.lock` updates.

The actual plugin source code lives at `/home/lirim/workspace/shopbite/shopware-plugin/` as a separate repository.

## Development Environment

All development runs inside Docker. The stack includes:
- **web** container: `ghcr.io/shopware/docker-dev:php8.4-node24-caddy`
  - Storefront: `http://localhost:8000`
  - Admin: `http://localhost:8080`
- **database**: MariaDB 11.8
- **opensearch**: OpenSearch 2

### Common Commands

```bash
make up              # Start Docker containers
make down            # Stop and remove containers
make shell           # SSH into the web container
make setup           # Install Shopware (drops and recreates DB)
make watch-storefront  # Start Storefront HMR dev server
make watch-admin       # Start Administration HMR dev server
make build-storefront  # Build Storefront assets
make build-administration  # Build Administration assets
```

Inside the web container (`make shell`), use standard Shopware CLI:

```bash
bin/console plugin:refresh
bin/console plugin:install --activate ShopBite
bin/console cache:clear
bin/console system:install --basic-setup --create-database --drop-database --force
```

## Production Build

Production images follow the official Shopware Docker guide (FrankenPHP base image, `shopware-cli project ci`, Deployment Helper). Everything is documented in `docs/production-docker.md`.

```bash
cp docker/prod.env.example docker/prod.env   # once, fill in secrets
make prod-build      # docker build --pull -f docker/Dockerfile
make prod-up         # compose.prod.yaml: db, valkey, init (deployment helper), web, worker, scheduler
make prod-deploy     # rebuild + roll out
make prod-console cmd="cache:clear"
```

Dokploy uses `compose.dokploy.yaml` (Compose type, full stack incl. MariaDB + Valkey, variables from `docker/dokploy.env.example`); the `init` service runs the Deployment Helper on every deploy.

### Dokploy (live)

Production runs on Dokploy (https://panel.shopbite.de, project "ShopBite", Compose service "shopware", compose path `./compose.dokploy.yaml`, auto-deploy on push to `main`). Public URL https://shopware.shopbite.de (service `web`, port 8000, TLS by Traefik). Every deploy rebuilds the image, runs `init` (Deployment Helper: migrations, plugin install/update, theme compile) and then recreates `web`, `worker`, `scheduler`. Environment variables are set in the Dokploy UI (template: `docker/dokploy.env.example`). The Dokploy API key and the Shopware integration credentials for this shop are in the workspace root `.env.local` (`DOKPLOY_API_KEY`, `SHOPWARE_ADMIN_KEY`, `SHOPWARE_ADMIN_SECRET`).

A second Compose service for the customer shop **Pizzeria La Fattoria** (Dokploy project "Pizzeria La Fattoria", appName `lafattoria-shopware-odg4uf`, https://backend.pizzeria-lafattoria.de) builds from the same repository but deploys **manually only** (`autoDeploy` off). It uses the customer's Hetzner Object Storage buckets and `IMAGE=lafattoria/shopware`. Migration steps from the old installation (https://shopware.veliu.net) are in `docs/production-docker.md` ("Migrating an existing shop into this stack").

Gotchas learned the hard way: the FrankenPHP base image inherits a Caddy healthcheck, so non-web services disable it; the base Caddyfile sends no `Cache-Control` for static files, hence `docker/Caddyfile`; Dokploy attaches only the domain service to `dokploy-network`; UI env vars are only available through `${VAR}` interpolation; `shopware-cli project ci` is the deploy build (there is no `project prod`).

`src/Filesystem/` holds the only project PHP code: a decorator that adds `Cache-Control` metadata to S3 uploads (`config.options.cache_control`).

Key files: `docker/Dockerfile`, `docker/Caddyfile`, `.dockerignore`, `.shopware-project.yml`, `compose.prod.yaml`, `compose.dokploy.yaml`, `config/packages/prod/shopware.yaml` (Redis wiring), `config/packages/prod/monolog.yaml` (stderr JSON logs). Production config under `config/packages/prod/` requires a Redis/Valkey instance via `REDIS_URL` and an S3 bucket via `S3_*` (media, thumbnails, theme, sitemap, private files; bundles stay in the image).

## Demo Data

`scripts/seed-demo-menu.py <integration-key> <integration-secret> [--dry]` seeds the "Demo" sales channel with the La Fattoria menu (`scripts/lafattoria.json`): 9 categories under "Speisekarte", 71 products plus 66 variants (pizza sizes, side dish and doneness for meat), property groups (Hauptzutaten, Vegetarisch, Vegan, Größe, Beilage, Garstufe), "Extras" cross-sellings on pizzas and the footer navigation (root folder "Footer" set as `footerCategoryId`). It is idempotent (IDs derived from menu numbers) and follows the storefront data model documented in `storefront/CLAUDE.md` ("Product data model"). Data rules: side dishes are standalone products, never cross-selling extras; vegan products carry only the Vegan flag; no "Küche" property.

## Plugin Architecture

The `shopbite-de/shopware-plugin` (namespace `ShopBite\`) adds headless Store API endpoints and checkout enhancements for the ShopBite Nuxt storefront. Key areas:

### Store API Routes (`/store-api/shopbite/*`)
All routes follow the abstract-base + concrete-implementation pattern and are declared in `src/Resources/config/routes.xml`:
- `/store-api/shopbite/business-hour` — Business hours per sales channel (day of week, open/close times)
- `/store-api/shopbite/holiday` — Holiday/closure dates per sales channel
- `/store-api/shopbite/multi-channel-group` — Sales channel groupings with domain associations
- `/store-api/shopbite/config` — Plugin system config (`isCheckoutEnabled`, `defaultDeliveryTime`)

### Entities (Shopware DAL)
Four custom entity tables via migrations:
- `shopbite_business_hour` / `shopbite_holiday` — linked to `sales_channel_id`
- `shopbite_multi_channel_group` — groups multiple sales channels
- `shopbite_voucher` + `shopbite_voucher_redemption` — voucher system with multi-currency price fields and redemption history

`SalesChannelExtension` adds `shopbiteBusinessHours` and `shopbiteHolidays` associations to the built-in SalesChannel entity.

### Checkout Enhancements
- **ContainerLineItemFactory** — registers the custom `container` line item type for bundled products
- **ReceiptPrintTypeProcessor** — a `CartProcessorInterface` + `CartDataCollectorInterface` that reads the `shopbite_receipt_print_type` product custom field and injects it into the cart line item payload

### Custom Fields (managed by `CustomFieldsInstaller`)
- **Products**: `shopbite_delivery_time_factor` (int), `shopbite_receipt_print_type` (select: `label`/`number`)
- **Categories**: `shopbite_category_icon` (text, icon name from icones.js.org)

## Plugin Testing and Code Quality

Run these inside the plugin directory (`/home/lirim/workspace/shopbite/shopware-plugin/`):

```bash
make test         # PHPUnit unit tests (vendor/bin/phpunit)
make cs-fix       # Auto-fix code style (PSR-12 + project rules)
make cs-check     # Dry-run style check with diffs
make psalm        # Static analysis (error level 3)
make check        # cs-check + psalm + test
```

PHPUnit config: `phpunit.xml` — tests under `tests/Unit/`, random execution order, coverage from `src/`.

Code style enforced via `.php-cs-fixer.dist.php`: PSR-12 base, short array syntax, alphabetical imports, strict types required.

## Updating the Plugin

To update the plugin version in this Shopware installation:

1. In the plugin repo, tag/release a new version
2. In this repo, run `composer update shopbite-de/shopware-plugin` inside the web container
3. Commit the updated `composer.lock`