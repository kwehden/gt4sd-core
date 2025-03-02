"""S3 storage utilities."""

import logging
import os
from typing import List, Optional, Set

from minio import Minio

from .exceptions import S3SyncError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class GT4SDS3Client:
    def __init__(
        self, host: str, access_key: str, secret_key: str, secure: bool = True
    ) -> None:
        """
        Construct an S3 client.

        Args:
            host: s3 host address.
            access_key: s3 access key.
            secret_key: s3 secret key.
            secure: whether the connection is secure or not. Defaults
                to True.
        """
        self.host = host
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.client = Minio(
            self.host,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def list_bucket_names(self) -> List[str]:
        """
        List all available s3 bucket names.

        Returns:
             List[str]: list with bucket names.
        """
        return [bucket.name for bucket in self.client.list_buckets()]

    def list_object_names(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        """
        List all available objects (recursive) in the given bucket based on a given prefix.

        Args:
            bucket: bucket name to search for objects.
            prefix: prefix for objects in the bucket.
                Defaults to None, a.k.a., no prefix filter.

        Returns:
            List[str]: list with object names.
        """
        return [
            s3_object.object_name
            for s3_object in self.client.list_objects(
                bucket_name=bucket, prefix=prefix, recursive=True
            )
        ]

    def list_directories(self, bucket: str, prefix: Optional[str] = None) -> Set[str]:
        """
        List all available "directories" in the given bucket based on a given prefix.

        Args:
            bucket: bucket name to search for objects.
            prefix: prefix for objects in the bucket.
                Defaults to None, a.k.a., no prefix filter.
                Needs to be a "directory" itself.

        Returns:
            List[str]: list with directory names.
        """
        if prefix:
            prefix = prefix + "/" if prefix[-1] != "/" else prefix
        return set(
            s3_object.object_name[len(prefix) if prefix else 0 : -1]
            for s3_object in self.client.list_objects(
                bucket_name=bucket, prefix=prefix, recursive=False
            )
            if s3_object.object_name[-1] == "/"
        )

    def sync_folder(
        self, bucket: str, path: str, prefix: Optional[str] = None, force: bool = False
    ) -> None:
        """Sync an entire folder from S3 recursively and save it under the given path.

        If :obj:`prefix` is given, every file under ``prefix/`` in S3 will be saver under ``path/`` in disk (i.e.
        ``prefix/`` is replaced by ``path/``).


        Args:
            bucket: bucket name to search for objects.
            path: path to save the objects in disk.
            prefix: prefix for objects in the bucket. Defaults to None, a.k.a., no prefix filter.
            force: force download even if a file with the same name is present. Defaults to False.
        """
        if not os.path.exists(path):
            logger.warning(f"path {path} does not exist, creating it...")
            os.makedirs(path)
        s3_objects = self.client.list_objects(
            bucket_name=bucket, prefix=prefix, recursive=True
        )
        for s3_object in s3_objects:
            object_name = s3_object.object_name
            object_name_stripped_prefix = (
                os.path.relpath(object_name, prefix) if prefix else object_name
            )
            filepath = os.path.join(path, object_name_stripped_prefix)
            # check for existence
            do_download = not os.path.exists(filepath)
            if do_download or force:
                logger.info(f"downloading file {object_name} in {filepath}")
                self.client.fget_object(
                    bucket_name=bucket, object_name=object_name, file_path=filepath
                )


def sync_folder_with_s3(
    host: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    folder_path: str,
    prefix: Optional[str] = None,
    secure: bool = True,
) -> None:
    """
    Sync the cache with the S3 remote storage.

    Args:
        host: s3 host address.
        access_key: s3 access key.
        secret_key: s3 secret key.
        bucket: bucket name to search for objects.
        folder_path: folder path.
        prefix: prefix for objects in the bucket. Defaults to None, a.k.a., no prefix filter.
        secure: whether the connection is secure or not. Defaults
            to True.

    Raises:
        S3SyncError: in case of S3 syncing errors.
    """
    path = os.path.join(folder_path, prefix) if prefix else folder_path
    try:
        client = GT4SDS3Client(
            host=host, access_key=access_key, secret_key=secret_key, secure=secure
        )
        logger.info("starting syncing")
        client.sync_folder(bucket=bucket, path=path, prefix=prefix)
        logger.info("syncing complete")
    except Exception:
        logger.exception("generic syncing error")
        raise S3SyncError(
            "CacheSyncingError",
            f"error in syncing path={path} with host={host} access_key={access_key} secret_key={secret_key} secure={secure} bucket={bucket}",
        )
