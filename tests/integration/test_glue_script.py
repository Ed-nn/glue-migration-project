import pytest
from pyspark.sql import SparkSession
import tempfile
import os
import pandas as pd
from pyspark.sql.functions import lit

@pytest.fixture(scope="session")
def spark():
    return (SparkSession.builder
            .master("local[1]")
            .appName("test")
            .getOrCreate())

@pytest.fixture
def sample_data():
    # Create sample data
    hired_employees = pd.DataFrame({
        'id': [1, 2],
        'name': ['John Doe', 'Jane Smith'],
        'datetime': ['2021-01-01T00:00:00Z', '2021-01-02T00:00:00Z'],
        'department_id': [1, 2],
        'job_id': [1, 2]
    })
    
    departments = pd.DataFrame({
        'id': [1, 2],
        'department': ['HR', 'IT']
    })
    
    jobs = pd.DataFrame({
        'id': [1, 2],
        'job': ['Manager', 'Developer']
    })
    
    return {
        'hired_employees': hired_employees,
        'departments': departments,
        'jobs': jobs
    }

def test_data_processing(spark, sample_data, mock_aws_services):
    # GIVEN
    s3_client = mock_aws_services['s3']
    bucket_name = "test-bucket"
    
    # Create bucket
    s3_client.create_bucket(Bucket=bucket_name)
    
    # WHEN
    for table_name, df in sample_data.items():
        # Convert pandas DataFrame to Spark DataFrame
        spark_df = spark.createDataFrame(df)
        
        # Process the data
        processed_df = spark_df.withColumn("processed", lit(True))
        
        # Verify data
        assert processed_df.count() == df.shape[0]
        assert "processed" in processed_df.columns
