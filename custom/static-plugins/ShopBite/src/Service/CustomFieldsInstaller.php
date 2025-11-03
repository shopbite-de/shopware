<?php

declare(strict_types=1);

namespace Veliu\ShopBite\Service;

use Shopware\Core\Defaults;
use Shopware\Core\Framework\Context;
use Shopware\Core\Framework\DataAbstractionLayer\EntityRepository;
use Shopware\Core\Framework\DataAbstractionLayer\Search\Criteria;
use Shopware\Core\Framework\DataAbstractionLayer\Search\Filter\EqualsFilter;
use Shopware\Core\System\CustomField\Aggregate\CustomFieldSet\CustomFieldSetCollection;
use Shopware\Core\System\CustomField\Aggregate\CustomFieldSetRelation\CustomFieldSetRelationCollection;
use Shopware\Core\System\CustomField\CustomFieldTypes;

final readonly class CustomFieldsInstaller
{
    private const string CUSTOM_FIELDSET_NAME = 'veliu_shopbite_product_set';

    private const array CUSTOM_FIELDSET = [
        'id' => '0198be8b24a0722cac46b07e3a80f49b',
        'name' => self::CUSTOM_FIELDSET_NAME,
        'config' => [
            'label' => [
                'en-GB' => 'ShopBite',
                'de-DE' => 'ShopBite',
                Defaults::LANGUAGE_SYSTEM => 'ShopBite',
            ],
        ],
        'customFields' => [
            [
                'id' => '0198be8b24a0722cac46b07e3a9686ec',
                'name' => 'veliu_shopbite_delivery_time_factor',
                'type' => CustomFieldTypes::INT,
                'config' => [
                    'label' => [
                        'en-GB' => 'Delivery Time Factor',
                        'de-DE' => 'Lieferzeitfaktor',
                        Defaults::LANGUAGE_SYSTEM => 'Delivery Time Factor',
                    ],
                    'customFieldPosition' => 1,
                ],
            ],
        ],
    ];

    /**
     * @param EntityRepository<CustomFieldSetCollection>         $customFieldSetRepository
     * @param EntityRepository<CustomFieldSetRelationCollection> $customFieldSetRelationRepository
     */
    public function __construct(
        private EntityRepository $customFieldSetRepository,
        private EntityRepository $customFieldSetRelationRepository,
    ) {
    }

    public function install(Context $context): void
    {
        $this->customFieldSetRepository->upsert([
            self::CUSTOM_FIELDSET,
        ], $context);
    }

    public function update(Context $context): void
    {
        $this->install($context);
    }

    public function uninstall(Context $context): void
    {
        $this->customFieldSetRepository->delete(self::CUSTOM_FIELDSET['customFields'], $context);
        $this->customFieldSetRelationRepository->delete([self::CUSTOM_FIELDSET], $context);
    }

    public function addRelations(Context $context): void
    {
        $this->customFieldSetRelationRepository->upsert(array_map(function (string $customFieldSetId) {
            return [
                'id' => '0198be99dd757130a9a99df0f878bf05',
                'customFieldSetId' => $customFieldSetId,
                'entityName' => 'product',
            ];
        }, $this->getCustomFieldSetIds($context)), $context);
    }

    /**
     * @return string[]
     */
    private function getCustomFieldSetIds(Context $context): array
    {
        $criteria = new Criteria();

        $criteria->addFilter(new EqualsFilter('name', self::CUSTOM_FIELDSET_NAME));

        return $this->customFieldSetRepository->searchIds($criteria, $context)->getIds();
    }
}
