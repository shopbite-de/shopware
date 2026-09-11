<?php declare(strict_types=1);

namespace App\Filesystem;

use League\Flysystem\FilesystemAdapter;
use Shopware\Core\Framework\Adapter\Filesystem\Adapter\AdapterFactoryInterface;
use Shopware\Core\Framework\Adapter\Filesystem\Adapter\S3ClientFactory;

/**
 * Decorates Shopware's "amazon-s3" adapter factory. When a filesystem is configured with
 *
 *   config:
 *     options:
 *       cache_control: 'public, max-age=31536000, immutable'
 *
 * the created adapter writes that Cache-Control header with every object. Without the
 * option the core factory is used unchanged. Registered in config/services.yaml.
 */
final class CacheControlAwsS3Factory implements AdapterFactoryInterface
{
    public function __construct(
        private readonly AdapterFactoryInterface $inner,
        private readonly int $batchWriteSize,
    ) {
    }

    public function create(array $config): FilesystemAdapter
    {
        $cacheControl = $config['options']['cache_control'] ?? null;

        if (!\is_string($cacheControl) || $cacheControl === '') {
            return $this->inner->create($config);
        }

        // S3ClientFactory only accepts known keys; cache_control is ours
        unset($config['options']['cache_control']);

        $result = S3ClientFactory::create($config);

        $adapter = new CacheControlS3Adapter($result['client'], $result['bucket'], $result['root'], $cacheControl);
        $adapter->batchSize = max(1, $this->batchWriteSize);

        return $adapter;
    }

    public function getType(): string
    {
        return $this->inner->getType();
    }
}
