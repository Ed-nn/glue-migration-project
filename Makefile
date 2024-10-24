.PHONY: build deploy destroy synth diff shell test clean

# Default environment
ENV ?= dev

# Build Docker images
build:
	docker-compose build

# Start shell in container
shell:
	docker-compose run --rm cdk

# Run tests
test:
	docker-compose run --rm test

# Deploy stack
deploy:
	cdk deploy -c env=$(ENV)

# Destroy stack
destroy:
	cdk destroy -c env=$(ENV)

# Synthesize stack
synth:
	cdk synth -c env=$(ENV)

# Show differences
diff:
	cdk diff -c env=$(ENV)

# Clean up
clean:
	docker-compose down
	rm -rf cdk.out
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +

# Run linting
lint:
	docker-compose run --rm test flake8 .
	docker-compose run --rm test black . --check
	docker-compose run --rm test isort . --check-only

# Format code
format:
	docker-compose run --rm test black .
	docker-compose run --rm test isort .