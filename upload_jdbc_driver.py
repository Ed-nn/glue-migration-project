#!/usr/bin/env python3

import boto3
import requests
import os

def download_jdbc_driver():
    """Download PostgreSQL JDBC driver"""
    driver_url = "https://jdbc.postgresql.org/download/postgresql-42.5.2.jar"
    local_path = "postgresql-42.5.2.jar"
    
    print("Downloading PostgreSQL JDBC driver...")
    response = requests.get(driver_url)
    with open(local_path, 'wb') as f:
        f.write(response.content)
    return local_path

def upload_to_s3(bucket_name, file_path):
    """Upload driver to S3"""
    s3 = boto3.client('s3')
    key = "jdbc-drivers/postgresql-42.5.2.jar"
    
    print(f"Uploading driver to s3://{bucket_name}/{key}")
    s3.upload_file(file_path, bucket_name, key)
    return key

def main():
    # Get bucket name from CloudFormation stack
    cf = boto3.client('cloudformation')
    response = cf.describe_stacks(StackName="GlueMigrationStack")
    outputs = response['Stacks'][0]['Outputs']
    bucket_name = next(
        output['OutputValue'] 
        for output in outputs 
        if output['OutputKey'] == 'DataLakeBucketName'
    )
    
    try:
        # Download and upload driver
        local_path = download_jdbc_driver()
        key = upload_to_s3(bucket_name, local_path)
        
        print(f"\nJDBC driver uploaded successfully!")
        print(f"S3 path: s3://{bucket_name}/{key}")
        
        # Cleanup local file
        os.remove(local_path)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise e

if __name__ == "__main__":
    main()