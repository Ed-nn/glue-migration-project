#!/usr/bin/env python3

import boto3
import os
from datetime import datetime
import json
from botocore.exceptions import ClientError

class S3Uploader:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.cloudformation = boto3.client('cloudformation')
        
    def get_bucket_name(self):
        """Get bucket name from CloudFormation outputs"""
        try:
            response = self.cloudformation.describe_stacks(
                StackName='GlueMigrationStack'
            )
            outputs = response['Stacks'][0]['Outputs']
            for output in outputs:
                if output['OutputKey'] == 'DataLakeBucketName':
                    return output['OutputValue']
            raise Exception("Bucket name not found in stack outputs")
        except ClientError as e:
            print(f"Error getting bucket name: {str(e)}")
            raise

    def create_sample_data(self):
        """Create sample CSV files"""
        # Hired Employees data with more records across different dates
        hired_employees_data = """id,name,datetime,department_id,job_id
4535,Marcelo Gonzalez,2021-07-27T16:02:08Z,1,2
4572,Lidia Mendez,2021-07-27T19:04:09Z,1,2
4689,Jorge Rodriguez,2021-07-28T10:15:30Z,2,1
4734,Maria Garcia,2021-07-29T14:20:45Z,3,3
4789,Carlos Lopez,2021-07-30T09:45:12Z,2,2
4812,Ana Martinez,2021-07-30T11:30:00Z,4,5
4834,Pedro Sanchez,2021-07-30T14:15:20Z,5,4
4856,Laura Torres,2021-07-30T16:45:10Z,1,3"""

        # Departments data
        departments_data = """id,department
1,Supply Chain
2,Maintenance
3,Staff
4,Operations
5,Engineering"""

        # Jobs data
        jobs_data = """id,job
1,Recruiter
2,Manager
3,Analyst
4,Engineer
5,Director"""

        # Write to files
        with open('hired_employees.csv', 'w') as f:
            f.write(hired_employees_data)
        with open('departments.csv', 'w') as f:
            f.write(departments_data)
        with open('jobs.csv', 'w') as f:
            f.write(jobs_data)

    def get_partition_info(self, datetime_str=None):
        """Get partition information from datetime"""
        if datetime_str:
            # Parse the datetime from the data
            dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        else:
            # Use current datetime
            dt = datetime.now()
            
        return {
            'year': dt.strftime("%Y"),
            'month': dt.strftime("%m"),
            'day': dt.strftime("%d")
        }

    def process_and_upload_hired_employees(self, bucket_name, file_path):
        """Process and upload hired_employees data with date-based partitioning"""
        print("\nProcessing hired_employees.csv...")
        
        # Read the file and group by date
        date_groups = {}
        with open(file_path, 'r') as f:
            header = f.readline().strip()  # Save header
            for line in f:
                # Extract datetime from the line
                fields = line.strip().split(',')
                datetime_str = fields[2]  # datetime is the third field
                
                # Get partition info
                partition = self.get_partition_info(datetime_str)
                partition_key = f"{partition['year']}-{partition['month']}-{partition['day']}"
                
                if partition_key not in date_groups:
                    date_groups[partition_key] = [header]  # Initialize with header
                date_groups[partition_key].append(line.strip())

        # Upload each group to its partition
        for partition_key, lines in date_groups.items():
            year, month, day = partition_key.split('-')
            s3_path = f"raw/hired_employees/year={year}/month={month}/day={day}/hired_employees.csv"
            
            # Create temporary file for this partition
            temp_file = f'hired_employees_{partition_key}.csv'
            with open(temp_file, 'w') as f:
                f.write('\n'.join(lines))
            
            # Upload file
            try:
                self.s3.upload_file(temp_file, bucket_name, s3_path)
                print(f"Uploaded partition: s3://{bucket_name}/{s3_path}")
            finally:
                os.remove(temp_file)  # Clean up temporary file

    def upload_reference_data(self, bucket_name, file_name, table_name):
        """Upload reference data (departments and jobs)"""
        print(f"\nProcessing {file_name}...")
        
        # Get current partition info
        partition = self.get_partition_info()
        
        # Construct S3 path
        s3_path = f"raw/{table_name}/year={partition['year']}/month={partition['month']}/day={partition['day']}/{file_name}"
        
        # Upload file
        try:
            self.s3.upload_file(file_name, bucket_name, s3_path)
            print(f"Uploaded: s3://{bucket_name}/{s3_path}")
        except ClientError as e:
            print(f"Error uploading {file_name}: {str(e)}")
            raise

    def upload_all_files(self):
        """Upload all data files to appropriate S3 paths"""
        try:
            # Get bucket name
            bucket_name = self.get_bucket_name()
            print(f"Using bucket: {bucket_name}")

            # Create sample data if it doesn't exist
            if not all(os.path.exists(f) for f in ['hired_employees.csv', 'departments.csv', 'jobs.csv']):
                print("Creating sample data files...")
                self.create_sample_data()

            # Process and upload hired_employees with date partitioning
            self.process_and_upload_hired_employees(bucket_name, 'hired_employees.csv')

            # Upload reference data
            self.upload_reference_data(bucket_name, 'departments.csv', 'departments')
            self.upload_reference_data(bucket_name, 'jobs.csv', 'jobs')

            print("\nFile upload complete!")
            
            # List uploaded files
            print("\nVerifying uploads...")
            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name, Prefix='raw/'):
                for obj in page.get('Contents', []):
                    print(f"s3://{bucket_name}/{obj['Key']}")

        except Exception as e:
            print(f"Error in upload process: {str(e)}")
            raise

if __name__ == "__main__":
    uploader = S3Uploader()
    uploader.upload_all_files()