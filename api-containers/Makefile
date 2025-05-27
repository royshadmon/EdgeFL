# Parameters with defaults
CONTAINER_NAME ?= aggregator_server
IMAGE ?= edgefl:latest
PORT ?= 8080
ENV_FILE ?= edgefl/env_files/mnist-docker/mnist-agg.env

# Run container using docker-compose
run-container:
	@echo "Deploying container: $(CONTAINER_NAME) with image: $(IMAGE) on port: $(PORT) using env: $(ENV_FILE)"
	@mkdir -p docker_makefile
	@CONTAINER_NAME=$(CONTAINER_NAME) \
	IMAGE=$(IMAGE) \
	PORT=$(PORT) \
	ENV_FILE=$(ENV_FILE) \
	envsubst < docker-compose-template.yaml > docker-compose.yaml
	@docker-compose -f docker-compose.yaml up -d
	@echo "Container $(CONTAINER_NAME) started"
	@rm -f docker-compose.yaml

# Stop and remove the container
stop-container:
	@echo "Stopping container: $(CONTAINER_NAME)"
	@docker stop $(CONTAINER_NAME)
	@docker rm $(CONTAINER_NAME)