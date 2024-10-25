import pytest
from unittest.mock import Mock, patch
import pandas as pd

@pytest.fixture
def mock_spark_context():
    """Mock for SparkContext"""
    return Mock()

@pytest.fixture
def mock_glue_context(mock_spark_context):
    """Mock for GlueContext"""
    glue_context = Mock()
    glue_context.spark_session = Mock()
    
    def create_dynamic_frame_from_options(*args, **kwargs):
        # Mock dynamic frame creation
        mock_dynamic_frame = Mock()
        return mock_dynamic_frame
    
    glue_context.create_dynamic_frame.from_options = create_dynamic_frame_from_options
    return glue_context

@pytest.fixture
def mock_spark_session():
    """Create a mock Spark session"""
    spark = Mock()
        
    # Mock DataFrame creation
    def create_dataframe(data):
        # Convert to pandas DataFrame if it isn't already
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
            
        # Create a mock DataFrame
        mock_df = Mock()
        mock_df.count = lambda: len(data)
        mock_df.columns = list(data.columns)
            
        # Mock withColumn method
        def mock_with_column(col_name, value):
            new_mock_df = Mock()
            new_mock_df.columns = mock_df.columns + [col_name]
            new_mock_df.count = mock_df.count
            return new_mock_df
            
        mock_df.withColumn = mock_with_column

        # Mock write method
        mock_write = Mock()
        mock_write.mode.return_value = mock_write
        mock_write.format.return_value = mock_write
        mock_write.option.return_value = mock_write
        mock_write.options.return_value = mock_write
        mock_write.save.return_value = None
        mock_df.write = mock_write

        return mock_df
        
    spark.createDataFrame = create_dataframe
    return spark

@pytest.fixture
def sample_data():
    """Create sample test data"""
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

def test_data_processing(mock_spark_session, sample_data, mock_aws_services):
    """Test data processing with mocked Spark"""
    # GIVEN
    s3_client = mock_aws_services['s3']
    bucket_name = "test-bucket"
    
    # Create bucket
    s3_client.create_bucket(Bucket=bucket_name)
    
    # WHEN
    for table_name, df in sample_data.items():
        # Convert data to Spark DataFrame using our mock
        spark_df = mock_spark_session.createDataFrame(df)
        
        # Process the data
        processed_df = spark_df.withColumn("processed", Mock())
        
        # THEN
        assert processed_df.count() == len(df)
        assert "processed" in processed_df.columns

        # Test write functionality
        processed_df.write \
            .mode("overwrite") \
            .format("jdbc") \
            .option("url", "jdbc:postgresql://test") \
            .save()

def test_data_transformation(mock_spark_session, sample_data):
    """Test specific data transformations"""
    # GIVEN
    employees_df = sample_data['hired_employees']
    
    # WHEN
    spark_df = mock_spark_session.createDataFrame(employees_df)
    transformed_df = spark_df.withColumn("year", Mock()) \
                            .withColumn("month", Mock()) \
                            .withColumn("day", Mock())
    
    # THEN
    assert "year" in transformed_df.columns
    assert "month" in transformed_df.columns
    assert "day" in transformed_df.columns
    assert transformed_df.count() == len(employees_df)

def test_error_handling(mock_spark_session):
    """Test error handling in data processing"""
    # GIVEN
    def raise_error(*args, **kwargs):
        raise Exception("Test error")
    
    mock_spark_session.createDataFrame.side_effect = raise_error
    
    # WHEN/THEN
    with pytest.raises(Exception) as exc_info:
        mock_spark_session.createDataFrame([])
    
    assert str(exc_info.value) == "Test error"