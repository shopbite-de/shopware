<?php

declare(strict_types=1);

namespace Veliu\ShopBite\Service;

use Shopware\Core\Checkout\Cart\LineItem\LineItem;
use Shopware\Core\Checkout\Cart\LineItem\LineItemCollection;
use Shopware\Core\Checkout\Cart\LineItemFactoryHandler\LineItemFactoryInterface;
use Shopware\Core\System\SalesChannel\SalesChannelContext;

final readonly class ChildrenLineItemFactory implements LineItemFactoryInterface
{
    public const string TYPE = 'container';

    #[\Override]
    public function supports(string $type): bool
    {
        return self::TYPE === $type;
    }

    #[\Override]
    public function create(array $data, SalesChannelContext $context): LineItem
    {
        $lineItem = new LineItem($data['id'], self::TYPE);

        $lineItem->setLabel($data['label'] ?? null);
        $lineItem->markModified();

        $lineItem->setRemovable(true);
        $lineItem->setStackable(true);

        $this->update($lineItem, $data, $context);

        return $lineItem;
    }

    #[\Override]
    public function update(LineItem $lineItem, array $data, SalesChannelContext $context): void
    {
        if (isset($data['payload'])) {
            $lineItem->setPayload($data['payload'] ?? []);
        }

        if (isset($data['quantity'])) {
            $lineItem->setQuantity((int) $data['quantity']);
        }

        if (!empty($data['children'])) {
            $children = new LineItemCollection();
            foreach ($data['children'] as $child) {
                $children->add(new LineItem($child['id'], 'product', $child['referencedId'] ?? $child['id'], $child['quantity'] ?? 1));
            }

            $lineItem->setChildren($children);
        }
    }
}
