<?php declare(strict_types=1);

namespace App\Filesystem;

use AsyncAws\Core\Result;
use AsyncAws\S3\S3Client;
use League\Flysystem\AsyncAwsS3\PortableVisibilityConverter;
use League\Flysystem\Config;
use Shopware\Core\Framework\Adapter\Filesystem\Adapter\AsyncAwsS3WriteBatchAdapter;
use Shopware\Core\Framework\Adapter\Filesystem\Plugin\CopyBatchInput;

/**
 * S3 adapter that stores a Cache-Control header as object metadata on every upload.
 *
 * MinIO/S3 have no bucket-wide default headers, and Shopware only sets the content type.
 * All public URLs are versioned (upload timestamp / content hash), so a long immutable
 * cache lifetime is safe. Covers the regular Flysystem writes (media uploads, thumbnails,
 * sitemap) and Shopware's batch copy used for theme files.
 */
final class CacheControlS3Adapter extends AsyncAwsS3WriteBatchAdapter
{
    public function __construct(
        S3Client $client,
        string $bucket,
        string $prefix,
        private readonly string $cacheControl,
    ) {
        parent::__construct($client, $bucket, $prefix, new PortableVisibilityConverter());
    }

    public function write(string $path, string $contents, Config $config): void
    {
        parent::write($path, $contents, $this->withCacheControl($config));
    }

    /**
     * @param resource $contents
     */
    public function writeStream(string $path, $contents, Config $config): void
    {
        parent::writeStream($path, $contents, $this->withCacheControl($config));
    }

    /**
     * Same as the parent implementation, plus the CacheControl option on every putObject.
     */
    public function writeBatch(CopyBatchInput ...$files): void
    {
        $adapterClass = \get_parent_class(parent::class);
        \assert(\is_string($adapterClass));

        /** @var S3Client $s3Client */
        $s3Client = \Closure::bind(fn () => $this->client, $this, $adapterClass)();
        $bucketName = \Closure::bind(fn () => $this->bucket, $this, $adapterClass)();
        $mimeTypeDetector = \Closure::bind(fn () => $this->mimeTypeDetector, $this, $adapterClass)();
        $prefixer = \Closure::bind(fn () => $this->prefixer, $this, $adapterClass)();
        /** @var PortableVisibilityConverter $visibilityConverter */
        $visibilityConverter = \Closure::bind(fn () => $this->visibility, $this, $adapterClass)();

        foreach (array_chunk($files, $this->batchSize) as $filesBatch) {
            $requests = [];

            foreach ($filesBatch as $file) {
                $sourceFile = $file->getSourceFile();

                if (\is_string($sourceFile)) {
                    $sourceFile = @fopen($sourceFile, 'rb');

                    if ($sourceFile === false) {
                        continue;
                    }
                }

                $mimeType = $mimeTypeDetector->detectMimeType($file->getTargetFiles()[0], $sourceFile);

                foreach ($file->getTargetFiles() as $targetFile) {
                    /** @var 'private'|'public-read' $visibility */
                    $visibility = $visibilityConverter->visibilityToAcl($file->visibility);

                    $options = [
                        'Bucket' => $bucketName,
                        'Key' => $prefixer->prefixPath($targetFile),
                        'Body' => $sourceFile,
                        'ACL' => $visibility,
                        'CacheControl' => $this->cacheControl,
                    ];

                    if ($mimeType !== null) {
                        $options['ContentType'] = $mimeType;
                    }

                    $requests[] = $s3Client->putObject($options);
                }
            }

            foreach (Result::wait($requests) as $result) {
                $result->resolve();
            }

            foreach ($filesBatch as $file) {
                if (\is_resource($file->getSourceFile())) {
                    fclose($file->getSourceFile());
                }
            }
        }
    }

    private function withCacheControl(Config $config): Config
    {
        return $config->withDefaults(['CacheControl' => $this->cacheControl]);
    }
}
