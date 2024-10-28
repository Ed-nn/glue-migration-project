import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'input_bucket', 'input_path', 'table_name', 'connection_name'])

sc = SparkContext()
glueContext = GlueContext(sc)
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read data from S3
input_path = f"s3://{args['input_bucket']}/{args['input_path']}"
df = spark.read.parquet(input_path)

# Write data to the target database
glueContext.write_dynamic_frame.from_options(
    frame=DynamicFrame.fromDF(df, glueContext, "df"),
    connection_type="postgresql",
    connection_options={
        "dbtable": args['table_name'],
        "connectionName": args['connection_name']
    },
    transformation_ctx="write_data"
)

job.commit()
