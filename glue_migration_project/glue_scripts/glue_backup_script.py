import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from datetime import datetime

def backup_table(glueContext, connection_name, table_name, output_bucket):
    # Read data from RDS using JDBC connection
    df = glueContext.create_dynamic_frame.from_options(
        connection_type="postgresql",
        connection_options={
            "connectionName": connection_name,
            "dbtable": table_name
        },
        transformation_ctx=f"datasource_{table_name}"
    )

    # Convert to Spark DataFrame and write to S3 in AVRO format
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_path = f"s3://{output_bucket}/backup/{table_name}/{current_date}/"
    
    df.toDF().write.format("avro").mode("overwrite").save(output_path)
    print(f"Backed up {table_name} to {output_path}")

def main():
    # Get job parameters
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME',
        'connection_name',
        'output_bucket',
        'tables'
    ])

    sc = SparkContext()
    glueContext = GlueContext(sc)
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)

    connection_name = args['connection_name']
    output_bucket = args['output_bucket']
    tables = args['tables'].split(',')

    for table in tables:
        backup_table(glueContext, connection_name, table, output_bucket)

    job.commit()

if __name__ == "__main__":
    main()
