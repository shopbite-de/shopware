<?php

declare(strict_types=1);

namespace Veliu\ShopBite\Core\Content\ShopBite\SalesChannel;

use Shopware\Core\Framework\DataAbstractionLayer\Search\Criteria;
use Shopware\Core\System\SalesChannel\SalesChannelContext;

abstract class AbstractShopBiteRoute
{
    abstract public function getDecorated(): self;

    abstract public function load(Criteria $criteria, SalesChannelContext $context): ShopBiteRouteResponse;
}
