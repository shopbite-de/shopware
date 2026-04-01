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