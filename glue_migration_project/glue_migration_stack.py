from aws_cdk import (
    Stack,
    aws_glue as glue,
    aws_s3 as s3,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_s3_assets as s3_assets,
    aws_events as events,
    aws_events_targets as targets,
    CfnOutput,
    RemovalPolicy,
    Duration,
    Tags,
)
from constructs import Construct
import os

class GlueMigrationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, env_name: str = "dev", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Project configuration
        project_name = "globant"
        application = "migration"
        base_name = f"{project_name}-{application}-{env_name}"
        db_name = "migration_db"

        # Create S3 bucket
        input_bucket = s3.Bucket(
            self, 
            "DataLakeBucket",
            bucket_name=f"{base_name}-data-lake".lower(),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
        )

        # Create VPC
        vpc = ec2.Vpc(
            self, 
            "MigrationVPC",
            vpc_name=f"{base_name}-vpc",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # Add VPC Endpoints
        vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # Create security group for Glue
        glue_security_group = ec2.SecurityGroup(
            self,
            "GlueSecurityGroup",
            vpc=vpc,
            description="Security group for Glue connection",
            security_group_name=f"{base_name}-glue-sg",
            allow_all_outbound=True
        )

        # Allow all inbound traffic within the same security group
        glue_security_group.add_ingress_rule(
            peer=glue_security_group,
            connection=ec2.Port.all_traffic(),
            description="Allow all internal traffic"
        )

        # Create security group for RDS
        db_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for RDS instance",
            security_group_name=f"{base_name}-db-sg",
            allow_all_outbound=True
        )

        # Add inbound rule for PostgreSQL from Glue
        db_security_group.add_ingress_rule(
            peer=glue_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access from Glue"
        )

        # Also allow public access for development purposes
        db_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access from anywhere"
        )

        # Create Secrets Manager secret
        db_secret = secretsmanager.Secret(
            self, 
            "DBCredentialsSecret",
            secret_name=f"{base_name}-db-secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "postgres", "dbname": "migration_db"}',
                generate_string_key="password",
                exclude_characters="/@\"'\\"
            )
        )

        # Create Parameter Group
        parameter_group = rds.ParameterGroup(
            self,
            "ParameterGroup",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            parameters={
                "max_connections": "100",
                "shared_buffers": "32768",
                "work_mem": "8192"
            }
        )

        # Create RDS instance
        db_instance = rds.DatabaseInstance(
            self, 
            "RDSInstance",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, 
                ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            security_groups=[db_security_group],
            credentials=rds.Credentials.from_secret(db_secret),
            database_name=db_name,
            port=5432,
            publicly_accessible=True,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            backup_retention=Duration.days(7),
            instance_identifier=f"{base_name}-db",
            parameter_group=parameter_group
        )

        # Create Glue IAM role
        glue_role = iam.Role(
            self, 
            "GlueJobRole",
            role_name=f"{base_name}-glue-role",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com")
        )

        # Add managed policy
        glue_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
        )

        # Add custom policies for S3
        glue_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket"
                ],
                resources=[
                    input_bucket.bucket_arn,
                    f"{input_bucket.bucket_arn}/*"
                ]
            )
        )

        # Create Glue Connection
        connection_name = f"{base_name}-postgres-connection"
        
        glue_connection = glue.CfnConnection(
            self,
            "GluePostgresConnection",
            catalog_id=Stack.of(self).account,
            connection_input=glue.CfnConnection.ConnectionInputProperty(
                name=connection_name,
                connection_type="JDBC",
                physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                    availability_zone=vpc.private_subnets[0].availability_zone,
                    security_group_id_list=[glue_security_group.security_group_id],
                    subnet_id=vpc.private_subnets[0].subnet_id
                ),
                connection_properties={
                    "JDBC_CONNECTION_URL": (
                        f"jdbc:postgresql://{db_instance.instance_endpoint.hostname}:"
                        f"{db_instance.instance_endpoint.port}/{db_name}"
                    ),
                    "USERNAME": "postgres",
                    "PASSWORD": db_secret.secret_value_from_json("password").unsafe_unwrap()
                }
            )
        )

        # Create Glue script asset
        glue_script_asset = s3_assets.Asset(
            self,
            "GlueScriptAsset",
            path=os.path.join(os.path.dirname(__file__), "glue_scripts", "glue_migration_script.py")
        )

        glue_script_asset.grant_read(glue_role)

        # Create Glue job
        glue_job = glue.CfnJob(
            self, 
            "GlueMigrationJob",
            name=f"{base_name}-etl-job",
            role=glue_role.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=glue_script_asset.s3_object_url
            ),
            connections=glue.CfnJob.ConnectionsListProperty(
                connections=[connection_name]
            ),
            default_arguments={
                "--input_bucket": input_bucket.bucket_name,
                "--connection_name": connection_name,
                "--job-language": "python",
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
                "--enable-spark-ui": "true",
                "--TempDir": f"s3://{input_bucket.bucket_name}/temporary",
                "--region": Stack.of(self).region,
                # Spark tuning
                "--conf spark.sql.broadcastTimeout": "3600",
                "--conf spark.sql.shuffle.partitions": "10",
                "--conf spark.default.parallelism": "10",
                "--conf spark.dynamicAllocation.enabled": "true",
                "--conf spark.dynamicAllocation.minExecutors": "2",
                "--conf spark.dynamicAllocation.maxExecutors": "4"
            },
            glue_version="4.0",
            worker_type="G.1X",
            number_of_workers=2,
            timeout=2880,
            execution_property=glue.CfnJob.ExecutionPropertyProperty(
                max_concurrent_runs=1
            )
        )
        # Add dependency to ensure connection is created before the Glue job
        glue_job.node.add_dependency(glue_connection)

        backup_script_asset = s3_assets.Asset(
            self,
            "GlueBackupScriptAsset",
            path=os.path.join(os.path.dirname(__file__), "glue_scripts", "glue_backup_script.py")
        )

        backup_script_asset.grant_read(glue_role)

        # Create Glue backup job
        backup_job = glue.CfnJob(
            self, 
            "GlueBackupJob",
            name=f"{base_name}-backup-job",
            role=glue_role.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=backup_script_asset.s3_object_url
            ),
            connections=glue.CfnJob.ConnectionsListProperty(
                connections=[connection_name]
            ),
            default_arguments={
                "--connection_name": connection_name,
                "--output_bucket": input_bucket.bucket_name,
                "--tables": "hired_employees,departments,jobs",  # Add all your table names here
                "--job-language": "python",
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
                "--enable-spark-ui": "true",
                "--TempDir": f"s3://{input_bucket.bucket_name}/temporary",
                "--region": Stack.of(self).region,
            },
            glue_version="4.0",
            worker_type="G.1X",
            number_of_workers=2,
            timeout=2880,
            execution_property=glue.CfnJob.ExecutionPropertyProperty(
                max_concurrent_runs=1
            )
        )

        # Create EventBridge rule to schedule the backup job
        schedule = events.Rule(
            self,
            "BackupJobSchedule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="0",
                month="*",
                week_day="*",
                year="*"
            ),
        )
        
        # Create IAM role for EventBridge to start Glue job
        eventbridge_role = iam.Role(
            self,
            "EventBridgeGlueRole",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
        )
        
        # Add permission to start Glue job
        eventbridge_role.add_to_policy(iam.PolicyStatement(
            actions=["glue:StartJobRun"],
            resources=[f"arn:aws:glue:{self.region}:{self.account}:job/{backup_job.name}"]
        ))
        
        # Add target to EventBridge rule
        schedule.add_target(targets.AwsApi(
            action="startJobRun",
            service="Glue",
            parameters={
                "JobName": backup_job.name,
                "Arguments": {
                    "--connection_name": connection_name,
                    "--output_bucket": input_bucket.bucket_name,
                    "--tables": "hired_employees,departments,jobs",
                }
            },
            role=eventbridge_role
        ))
        # Add CloudFormation outputs
        CfnOutput(
            self, 
            "DataLakeBucketName",
            value=input_bucket.bucket_name,
            description="Data Lake Bucket Name"
        )

        CfnOutput(
            self, 
            "DBEndpoint",
            value=db_instance.instance_endpoint.hostname,
            description="RDS instance endpoint"
        )

        CfnOutput(
            self, 
            "DBPort",
            value=str(db_instance.instance_endpoint.port),
            description="RDS instance port"
        )

        CfnOutput(
            self, 
            "DBSecretName",
            value=db_secret.secret_name,
            description="Secrets Manager secret name"
        )

        CfnOutput(
            self, 
            "GlueJobName",
            value=glue_job.name,
            description="Glue Job Name"
        )

        CfnOutput(
            self, 
            "GlueConnectionName",
            value=connection_name,
            description="Glue Connection Name"
        )
        CfnOutput(
            self, 
            "GlueBackupJobName",
            value=backup_job.name,
            description="Glue Backup Job Name"
        )
        # Add tags
        Tags.of(self).add('Project', project_name)
        Tags.of(self).add('Application', application)
        Tags.of(self).add('Environment', env_name)
