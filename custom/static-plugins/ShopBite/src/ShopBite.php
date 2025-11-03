<?php

declare(strict_types=1);

namespace Veliu\ShopBite;

use Shopware\Core\Framework\Plugin;
use Shopware\Core\Framework\Plugin\Context\ActivateContext;
use Shopware\Core\Framework\Plugin\Context\InstallContext;
use Shopware\Core\Framework\Plugin\Context\UninstallContext;
use Shopware\Core\Framework\Plugin\Context\UpdateContext;
use Veliu\ShopBite\Service\CustomFieldsInstaller;

class ShopBite extends Plugin
{
    public function install(InstallContext $installContext): void
    {
        $this->getCustomFieldsInstaller()->install($installContext->getContext());
    }

    public function uninstall(UninstallContext $uninstallContext): void
    {
        parent::uninstall($uninstallContext);

        if ($uninstallContext->keepUserData()) {
            return;
        }

        $this->getCustomFieldsInstaller()->uninstall($uninstallContext->getContext());
    }

    public function activate(ActivateContext $activateContext): void
    {
        $this->getCustomFieldsInstaller()->addRelations($activateContext->getContext());
    }

    public function update(UpdateContext $updateContext): void
    {
        $this->getCustomFieldsInstaller()->update($updateContext->getContext());
    }

    private function getCustomFieldsInstaller(): CustomFieldsInstaller
    {
        if ($this->container->has(CustomFieldsInstaller::class)) {
            return $this->container->get(CustomFieldsInstaller::class);
        }

        return new CustomFieldsInstaller(
            $this->container->get('custom_field_set.repository'),
            $this->container->get('custom_field_set_relation.repository')
        );
    }
}
