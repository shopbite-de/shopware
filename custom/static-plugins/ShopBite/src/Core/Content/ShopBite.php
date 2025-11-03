<?php

declare(strict_types=1);

namespace Veliu\ShopBite\Core\Content;

use Shopware\Core\Framework\Struct\Struct;

final class ShopBite extends Struct
{
    public function __construct(
        public readonly bool $isCheckoutEnabled,
        public readonly int $deliveryTime,
    ) {
    }
}
