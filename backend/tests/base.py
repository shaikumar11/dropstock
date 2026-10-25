import json
import os
import unittest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")

from moto import mock_aws  # noqa: E402

from app import infra  # noqa: E402


class ApiTestCase(unittest.TestCase):
    """Each test gets a fresh in-memory DynamoDB with both tables created."""

    def setUp(self):
        self._mock = mock_aws()
        self._mock.start()
        infra.create_tables()

    def tearDown(self):
        self._mock.stop()

    @staticmethod
    def event(body=None, path_id=None, headers=None):
        return {
            "headers": headers or {},
            "pathParameters": {"id": path_id} if path_id else {},
            "body": json.dumps(body) if body is not None else None,
        }

    @staticmethod
    def parse(response):
        return response["statusCode"], json.loads(response["body"])
