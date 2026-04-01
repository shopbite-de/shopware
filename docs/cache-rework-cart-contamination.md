# CACHE_REWORK: Cart Cross-Contamination Bug

## Summary

Enabling `CACHE_REWORK` (`bin/console feature:enable CACHE_REWORK`) causes logged-in customers to receive another customer's cart after signing up or logging in. **Do not enable this feature flag in production until this is resolved.**

---

## Root Cause

### What CACHE_REWORK changes

The old system used `CacheStateSubscriber` to track `STATE_LOGGED_IN` and `STATE_CART_FILLED` per request. Routes tagged with those invalidation states were **never served from cache** for logged-in users or users with cart items — safe but conservative.

Under CACHE_REWORK:
- `CacheStateSubscriber` is completely disabled (`CacheStateSubscriber.php:47` returns empty subscribers)
- Pages for logged-in customers with filled carts **are now cached**
- Protection switches to `sw-cache-hash` cookie-based discrimination

### The cache key does not include the customer token

`sw-cache-hash` is computed from (`CacheHeadersService.php:97-104`):

```
rule IDs + version ID + currency ID + language ID + tax state + logged-in boolean
```

It does **not** include the individual customer's `sw-context-token`. Because `sw-context-token` travels as a request **header** (not a cookie), it is invisible to the cache key generator (`HttpCacheKeyGenerator.php:75-93`).

**Result: Every B2C customer with the same language, currency, and price rules shares the exact same `sw-cache-hash`.**

### The old state validator guard is skipped

`CacheStore.lookup()` previously called `CacheStateValidator.isValid()` to block logged-in/cart-filled customers from receiving cached responses. Under CACHE_REWORK this is explicitly skipped (`CacheStore.php:115-122`):

```php
if (!Feature::isActive('CACHE_REWORK') && ...) {
    $isValid = $this->stateValidator->isValid($request, $response);
    if (!$isValid) {
        return null;  // ← this protection is GONE under CACHE_REWORK
    }
}
```

### Failure scenario

1. Customer A logs in with 3 items in cart → `sw-cache-hash = HASH_LOGGED_IN`
2. A cacheable Storefront route (e.g. `NavigationController`) renders mini-cart state → cached under `hash(URI + HASH_LOGGED_IN)`
3. Customer B logs in with same currency/language/rules → `sw-cache-hash = HASH_LOGGED_IN` (identical)
4. Customer B requests the same page → **cache hit** → served Customer A's response

For the full cart: `CartLoadRoute` has no `#[HttpCache]` so Shopware's built-in cache gives it `Cache-Control: no-cache, private`. This protects the route from Shopware's own PHP cache. **However:**

- A Varnish/CDN that doesn't fully honour `Cache-Control: private` and uses the `Vary: sw-cache-hash` header Shopware now injects on all responses (`CacheHeadersService.php:42-49`) will cache the cart response keyed only by hash — causing direct cart contamination.
- Nuxt's SSR layer / Nitro cache has the same problem if it caches Store API responses without filtering `private` responses.

### Why it manifests specifically at signup/login

After registration/login, the client receives a new `sw-context-token` and an updated `sw-cache-hash` cookie. There is a **timing gap**: the very next GET request may still carry the old cookie value. Under the old system this was harmless (states blocked wrong cache entries). Under CACHE_REWORK the old hash may match another customer's valid cache entry, causing a wrong response during this transition window.

---

## Fix

### Short-term (safest)

Do not enable `CACHE_REWORK`. The feature is still marked `Experimental!` in `feature.yaml`.

### If CACHE_REWORK is needed: isolate logged-in customers in the cache hash

Listen to `HttpCacheCookieEvent` and add the context token to the hash for logged-in customers. This gives each customer a unique hash while guests still share cache entries:

```php
<?php declare(strict_types=1);

use Shopware\Core\Framework\Adapter\Cache\Event\HttpCacheCookieEvent;
use Shopware\Core\PlatformRequest;
use Symfony\Component\EventDispatcher\Attribute\AsEventListener;

#[AsEventListener]
class IsolateCustomerCacheHash
{
    public function __invoke(HttpCacheCookieEvent $event): void
    {
        if ($event->context->getCustomer() === null) {
            return; // guests can still share cache entries
        }

        $token = $event->request->headers->get(PlatformRequest::HEADER_CONTEXT_TOKEN)
            ?? $event->request->cookies->get(PlatformRequest::HEADER_CONTEXT_TOKEN);

        if ($token !== null) {
            $event->setPart('context-token', $token);
        }
    }
}
```

Register as a tagged service in `services.xml`:

```xml
<service id="ShopBite\...\IsolateCustomerCacheHash">
    <tag name="kernel.event_listener"/>
</service>
```

This restores per-customer cache isolation while keeping CACHE_REWORK's Store API caching benefits for unauthenticated users.

### Additionally: ensure reverse proxy respects Cache-Control: private

Configure Varnish, Cloudflare, or Nitro to never cache responses with `Cache-Control: private`. Without this, even the listener above may not be sufficient if the CDN layer ignores response directives.

---

## Key files involved

| File | Relevance |
|------|-----------|
| `vendor/shopware/core/Framework/Adapter/Cache/CacheStateSubscriber.php` | Disabled under CACHE_REWORK — removes `logged-in`/`cart-filled` protection |
| `vendor/shopware/core/Framework/Adapter/Cache/Http/CacheHeadersService.php` | Computes `sw-cache-hash` — context token is not included |
| `vendor/shopware/core/Framework/Adapter/Cache/Http/HttpCacheKeyGenerator.php` | Cache key uses only URI + static hash + cookies (not `sw-context-token` header) |
| `vendor/shopware/core/Framework/Adapter/Cache/Http/CacheStore.php:115` | `CacheStateValidator` guard is skipped under CACHE_REWORK |
| `vendor/shopware/core/Framework/Adapter/Cache/Http/CacheResponseSubscriber.php:118` | Store API caching enabled only when CACHE_REWORK is active |
| `vendor/shopware/core/Checkout/Cart/SalesChannel/CartLoadRoute.php` | No `#[HttpCache]` — cart gets `Cache-Control: private` from Shopware's own cache, but external proxies can still serve it wrong |