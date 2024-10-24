# Globant Migration Project

AWS Glue ETL project for data migration from CSV files to RDS PostgreSQL, built with AWS CDK.

## Project Structure

```
glue_migration_project/
├── .github/
│   └── workflows/
│       ├── development.yml
│       └── production.yml
├── config/
│   ├── environments/
│   │   ├── dev.yml
│   │   └── prod.yml
│   ├── s3_paths.yml
│   └── glue_config.yml
├── glue_migration_project/
│   ├── __init__.py
│   ├── glue_migration_stack.py
│   └── glue_scripts/
│       └── glue_migration_script.py
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   └── test_glue_migration_stack.py
│   └── integration/
│       └── test_glue_script.py
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
├── requirements.txt
└── requirements-dev.txt
```

## Prerequisites

- Docker and Docker Compose
- AWS CLI configured with appropriate credentials
- Make (optional, but recommended)

## Docker Setup

### Understanding the Docker Configuration

The project uses Docker to ensure consistent development and deployment environments. Two main services are defined:

1. **CDK Service**:
   - Main development environment
   - Includes AWS CDK CLI
   - Mounts AWS credentials
   - Used for deployments

2. **Test Service**:
   - Dedicated to running tests
   - Isolated test environment
   - Consistent across all environments

### Dockerfile Components

```dockerfile
FROM python:3.9-slim

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    nodejs \
    npm && \
    npm install -g aws-cdk

# Project dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

WORKDIR /app
```

### Docker Compose Services

```yaml
services:
  cdk:
    build: .
    volumes:
      - .:/app
      - ~/.aws:/root/.aws:ro
    environment:
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

  test:
    build: .
    volumes:
      - .:/app
    command: pytest
```

## Getting Started with Docker

1. Create environment file:
```bash
cat > .env << EOF
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
AWS_ACCOUNT_ID=your_account_id
ENVIRONMENT=dev
EOF
```

2. Build Docker images:
```bash
make build
```

3. Start development shell:
```bash
make shell
```

4. Inside the container:
```bash
# Synthesize stack
cdk synth

# Deploy stack
cdk deploy

# Run tests
pytest
```

## Common Docker Commands

### Development Workflow

```bash
# Start development shell
make shell

# Deploy to specific environment
make deploy ENV=dev

# Run tests
make test

# Show stack differences
make diff ENV=dev

# Clean up
make clean
```

### Testing with Docker

```bash
# Run all tests
make test

# Run specific test file
docker-compose run --rm test pytest tests/unit/test_glue_migration_stack.py

# Run with coverage
docker-compose run --rm test pytest --cov=glue_migration_project
```

### Debugging

```bash
# View container logs
docker-compose logs cdk

# Access running container
docker-compose exec cdk bash

# Check container status
docker-compose ps
```

## Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/Ed-nn/glue-migration-project.git
cd glue-migration-project
```

2. Build Docker container:
```bash
make build
```

3. Start development shell:
```bash
make shell
```

4. Deploy to development:
```bash
make deploy ENV=dev
```

## Deployment

### Development Environment
```bash
make deploy ENV=dev
```

### Production Environment
```bash
make deploy ENV=prod
```

## Data Upload

Upload CSV files to S3:
```bash
# Get bucket name
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name GlueMigrationStack \
    --query 'Stacks[0].Outputs[?OutputKey==`DataLakeBucketName`].OutputValue' \
    --output text)

# Upload files
aws s3 cp hired_employees.csv s3://$BUCKET_NAME/raw/hired_employees/
aws s3 cp departments.csv s3://$BUCKET_NAME/raw/departments/
aws s3 cp jobs.csv s3://$BUCKET_NAME/raw/jobs/
```

## Running Glue Job

```bash
# Get job name
JOB_NAME=$(aws cloudformation describe-stacks \
    --stack-name GlueMigrationStack \
    --query 'Stacks[0].Outputs[?OutputKey==`GlueJobName`].OutputValue' \
    --output text)

# Run job
aws glue start-job-run --job-name $JOB_NAME
```

## Infrastructure

- S3 bucket for data lake
- AWS Glue for ETL processing
- RDS PostgreSQL for data storage
- VPC with public and private subnets
- Security groups and IAM roles
- Secrets Manager for credentials

## CI/CD Pipeline

- GitHub Actions for CI/CD
- Docker-based testing and deployment
- Automatic deployments to development on push to develop branch
- Manual approval required for production deployments
- Security scanning and testing before deployment

## Best Practices

1. **Docker Usage**:
   - Always use `make` commands for common operations
   - Keep `.env` file out of version control
   - Update Docker image when adding new dependencies
   - Use volume mounts for development
   - Clean up with `make clean` regularly

2. **Development Workflow**:
   - Use the container for all development tasks
   - Run tests before commits
   - Keep dependencies updated
   - Follow the branching strategy

3. **Security**:
   - Never commit AWS credentials
   - Use environment variables
   - Follow least privilege principle
   - Regular security updates

## Contributing

1. Create a feature branch from develop
2. Make changes and add tests
3. Run tests and linting in Docker
4. Create pull request to develop
5. Await review and merge

