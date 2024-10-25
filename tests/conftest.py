# tests/conftest.py
import pytest
import boto3
from moto import mock_aws
import os

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture(scope="function")
def mock_aws_services(aws_credentials):
    with mock_aws():
        yield {
            "s3": boto3.client("s3", region_name="us-east-1"),
            "glue": boto3.client("glue", region_name="us-east-1"),
            "secretsmanager": boto3.client("secretsmanager", region_name="us-east-1")
        }