import os
import aws_cdk as cdk
from glue_migration_project.glue_migration_stack import GlueMigrationStack

app = cdk.App()

# Get environment from context or use default
env_name = app.node.try_get_context('env') or 'dev'

GlueMigrationStack(
    app, 
    "GlueMigrationStack",
    env_name=env_name,
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

app.synth()