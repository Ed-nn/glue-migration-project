import aws_cdk as cdk
import aws_cdk.assertions as assertions
from glue_migration_project.glue_migration_stack import GlueMigrationStack

def test_s3_bucket_created():
    # GIVEN
    app = cdk.App()
    # WHEN
    stack = GlueMigrationStack(app, "TestStack", env_name="test")
    template = assertions.Template.from_stack(stack)
    # THEN
    template.has_resource_properties("AWS::S3::Bucket", {})

def test_rds_instance_created():
    # GIVEN
    app = cdk.App()
    # WHEN
    stack = GlueMigrationStack(app, "TestStack", env_name="test")
    template = assertions.Template.from_stack(stack)
    # THEN
    template.has_resource_properties("AWS::RDS::DBInstance", {
        "Engine": "postgres"
    })

def test_glue_job_created():
    # GIVEN
    app = cdk.App()
    # WHEN
    stack = GlueMigrationStack(app, "TestStack", env_name="test")
    template = assertions.Template.from_stack(stack)
    # THEN
    template.has_resource_properties("AWS::Glue::Job", {
        "Command": {
            "Name": "glueetl",
            "PythonVersion": "3"
        },
        "GlueVersion": "4.0"
    })

def test_secret_created():
    # GIVEN
    app = cdk.App()
    # WHEN
    stack = GlueMigrationStack(app, "TestStack", env_name="test")
    template = assertions.Template.from_stack(stack)
    # THEN
    template.has_resource_properties("AWS::SecretsManager::Secret", {
        "GenerateSecretString": {
            "SecretStringTemplate": '{"username": "postgres", "dbname": "migration_db"}'
        }
    })

def test_vpc_created():
    # GIVEN
    app = cdk.App()
    # WHEN
    stack = GlueMigrationStack(app, "TestStack", env_name="test")
    template = assertions.Template.from_stack(stack)
    # THEN
    template.has_resource_properties("AWS::EC2::VPC", {
        "EnableDnsHostnames": True,
        "EnableDnsSupport": True
    })

def test_glue_connection_created():
    # GIVEN
    app = cdk.App()
    # WHEN
    stack = GlueMigrationStack(app, "TestStack", env_name="test")
    template = assertions.Template.from_stack(stack)
    # THEN
    template.has_resource_properties("AWS::Glue::Connection", {
        "ConnectionInput": {
            "ConnectionType": "JDBC"
        }
    })