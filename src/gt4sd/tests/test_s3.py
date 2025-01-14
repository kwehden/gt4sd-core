"""S3 storage tests.

These assume a bucket `gt4sd-ci-tests` and an artifact `a_folder/containing/a_file.txt`.
"""

import logging
import os
import shutil
import tempfile

import pytest

from gt4sd.s3 import GT4SDS3Client, sync_folder_with_s3
from gt4sd.tests.utils import GT4SDTestSettings

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

test_settings = GT4SDTestSettings.get_instance()


@pytest.fixture
def client() -> GT4SDS3Client:
    return GT4SDS3Client(
        host=test_settings.gt4sd_s3_host,
        access_key=test_settings.gt4sd_s3_access_key,
        secret_key=test_settings.gt4sd_s3_secret_key,
        secure=test_settings.gt4sd_s3_secure,
    )


def test_bucket_listing(client: GT4SDS3Client):
    bucket_names = client.list_bucket_names()
    assert isinstance(bucket_names, list)
    assert "gt4sd-ci-tests" in bucket_names


def test_object_listing(client: GT4SDS3Client):
    object_names = client.list_object_names(bucket="gt4sd-ci-tests", prefix="a_folder")
    assert isinstance(object_names, list)
    for object_name in object_names:
        assert object_name.endswith(".txt")


def test_directory_listing(client: GT4SDS3Client):
    object_names = client.list_directories(bucket="gt4sd-ci-tests", prefix="a_folder")
    assert isinstance(object_names, set)
    for object_name in object_names:
        assert object_name == "containing"


def test_sync_folder(client: GT4SDS3Client):
    directory = tempfile.mkdtemp()
    try:
        client.sync_folder("gt4sd-ci-tests", directory)
        filepaths = set(
            [filepath.replace(directory, "") for filepath in os.listdir(directory)]
        )
        objectpaths = set(
            map(
                lambda path: path.split("/")[0],
                client.list_object_names(bucket="gt4sd-ci-tests"),
            )
        )
        assert filepaths == objectpaths
    finally:
        logger.info(f"cleaning up test folder {directory}")
        shutil.rmtree(directory)


def test_sync_folder_with_s3(client):
    directory = tempfile.mkdtemp()
    try:
        sync_folder_with_s3(
            host=test_settings.gt4sd_s3_host,
            access_key=test_settings.gt4sd_s3_access_key,
            secret_key=test_settings.gt4sd_s3_secret_key,
            bucket="gt4sd-ci-tests",
            folder_path=directory,
            secure=test_settings.gt4sd_s3_secure,
        )
        filepaths = set(
            [filepath.replace(directory, "") for filepath in os.listdir(directory)]
        )
        objectpaths = set(
            map(
                lambda path: path.split("/")[0],
                client.list_object_names(bucket="gt4sd-ci-tests"),
            )
        )
        assert filepaths == objectpaths
    finally:
        logger.info(f"cleaning up test folder {directory}")
        shutil.rmtree(directory)
