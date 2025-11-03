<?php

declare(strict_types=1);

namespace Veliu\ShopBite\Core\Content\ShopBite\SalesChannel;

use Shopware\Core\Framework\Plugin\Exception\DecorationPatternException;
use Shopware\Core\System\SalesChannel\SalesChannelContext;
use Shopware\Core\System\SystemConfig\SystemConfigService;
use Symfony\Component\Routing\Attribute\Route;
use Veliu\ShopBite\Core\Content\ShopBite;

use function Psl\Type\bool;
use function Psl\Type\positive_int;

#[Route(defaults: ['_routeScope' => ['store-api']])]

class ShopBiteRoute
{
    public function __construct(
        private SystemConfigService $systemConfigService,
    ) {
    }

    public function getDecorated(): AbstractShopBiteRoute
    {
        throw new DecorationPatternException(self::class);
    }

    #[Route(
        path: '/store-api/pizza-toppings',
        name: 'store-api.veliu.delivery_time.get',
        defaults: ['_httpCache' => false],
        methods: ['GET']
    )]
    public function load(SalesChannelContext $context): ShopBiteRouteResponse
    {
        $isCheckoutEnabled = $this->systemConfigService->get('ShopBite.config.isCheckoutEnabled', $context->getSalesChannelId());
        $defaultDeliveryTime = $this->systemConfigService->get('ShopBite.config.defaultDeliveryTime', $context->getSalesChannelId());

        $isCheckoutEnabled = bool()->coerce($isCheckoutEnabled);
        $defaultDeliveryTime = positive_int()->coerce($defaultDeliveryTime);

        return new ShopBiteRouteResponse(new ShopBite($isCheckoutEnabled, $defaultDeliveryTime));
    }
}
