import sys
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import (
    current_timestamp, 
    col, 
    to_timestamp,
    lit,
    year,
    month,
    dayofmonth
)
from pyspark.sql.types import (
    StructType, 
    StructField, 
    StringType, 
    IntegerType, 
    TimestampType
)
from datetime import datetime

def get_table_schema(table_name):
    """Define schema for each table"""
    if table_name == 'hired_employees':
        return StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("datetime", StringType(), True),
            StructField("department_id", IntegerType(), True),
            StructField("job_id", IntegerType(), True)
        ])
    elif table_name == 'departments':
        return StructType([
            StructField("id", IntegerType(), True),
            StructField("department", StringType(), True)
        ])
    elif table_name == 'jobs':
        return StructType([
            StructField("id", IntegerType(), True),
            StructField("job", StringType(), True)
        ])
    else:
        raise ValueError(f"Unknown table: {table_name}")

def process_hired_employees(df):
    """Process hired_employees specific transformations"""
    return df.withColumn(
        "datetime", 
        to_timestamp(col("datetime"))
    ).withColumn(
        "department_id",
        col("department_id").cast(IntegerType())
    ).withColumn(
        "job_id",
        col("job_id").cast(IntegerType())
    ).withColumn(
        "id",
        col("id").cast(IntegerType())
    ).withColumn(
        "year",
        year(to_timestamp(col("datetime")))
    ).withColumn(
        "month",
        month(to_timestamp(col("datetime")))
    ).withColumn(
        "day",
        dayofmonth(to_timestamp(col("datetime")))
    )

def process_reference_table(df, current_date):
    """Process reference tables (departments and jobs)"""
    return df.withColumn(
        "year",
        lit(current_date.year)
    ).withColumn(
        "month",
        lit(current_date.month)
    ).withColumn(
        "day",
        lit(current_date.day)
    )

def write_to_postgresql(df, table_name, connection_name):
    """Write DataFrame to PostgreSQL using Glue connection"""
    try:
        print(f"Writing {table_name} to PostgreSQL...")
        
        # Remove partition columns before writing
        columns_to_write = [col for col in df.columns if col not in ['year', 'month', 'day']]
        df_to_write = df.select(*columns_to_write)
        
        # Get the connection information from Glue
        glue_client = boto3.client('glue')
        connection = glue_client.get_connection(Name=connection_name)
        jdbc_url = connection['Connection']['ConnectionProperties']['JDBC_CONNECTION_URL']
        
        # Write using the Glue connection
        df_to_write.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", table_name) \
            .option("user", connection['Connection']['ConnectionProperties']['USERNAME']) \
            .option("password", connection['Connection']['ConnectionProperties']['PASSWORD']) \
            .mode("overwrite") \
            .save()
        
        print(f"Successfully wrote {df_to_write.count()} rows to {table_name}")
    except Exception as e:
        print(f"Error writing to PostgreSQL: {str(e)}")
        raise e

def read_partitioned_data(glueContext, input_bucket, table_name, partition_date=None):
    """Read data from partitioned S3 location"""
    if partition_date is None:
        partition_date = datetime.now()
    
    # Get schema for the table
    schema = get_table_schema(table_name)
    
    # Construct base path
    base_path = f"s3://{input_bucket}/raw/{table_name}/"
    
    print(f"Reading from base path: {base_path}")
    
    # Read all partitions for the table
    df = glueContext.spark_session.read \
        .option("header", "true") \
        .option("inferSchema", "false") \
        .schema(schema) \
        .csv(base_path + "*/*/*/")
    
    print(f"Read {df.count()} records from {table_name}")
    return df

def main():
    print("Starting ETL job...")
    
    # Initialize Glue context
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)

    # Get job parameters
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME',
        'input_bucket',
        'connection_name'
    ])

    # Get parameters
    input_bucket = args['input_bucket']
    connection_name = args['connection_name']
    
    print(f"Using bucket: {input_bucket}")
    print(f"Using connection: {connection_name}")
    
    # Get current date for reference tables
    current_date = datetime.now()

    try:
        # Process hired_employees
        print("\nProcessing hired_employees...")
        hired_employees_df = read_partitioned_data(glueContext, input_bucket, "hired_employees")
        processed_employees_df = process_hired_employees(hired_employees_df)
        write_to_postgresql(processed_employees_df, "hired_employees", connection_name)

        # Process departments
        print("\nProcessing departments...")
        departments_df = read_partitioned_data(glueContext, input_bucket, "departments")
        processed_departments_df = process_reference_table(departments_df, current_date)
        write_to_postgresql(processed_departments_df, "departments", connection_name)

        # Process jobs
        print("\nProcessing jobs...")
        jobs_df = read_partitioned_data(glueContext, input_bucket, "jobs")
        processed_jobs_df = process_reference_table(jobs_df, current_date)
        write_to_postgresql(processed_jobs_df, "jobs", connection_name)

        print("\nETL job completed successfully!")

    except Exception as e:
        print(f"Error in ETL process: {str(e)}")
        raise e
    finally:
        job.commit()

if __name__ == "__main__":
    main()