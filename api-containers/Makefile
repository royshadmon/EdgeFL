# Parameters with defaults
NODE_TYPE ?= agg
CONTAINER_NAME ?= edgefl_container
IMAGE ?= edgefl:latest
PORT ?= 8080
ENV_FILE ?= edgefl/env_files/default.en


# Compose file template directory
COMPOSE_TEMPLATE := docker-compose-template.yaml
COMPOSE_FILE := docker-compose-$(CONTAINER_NAME).yaml

# Run container using docker-compose
up:
	@mkdir -p docker_makefile
	@NODE_TYPE=$(NODE_TYPE) \
	CONTAINER_NAME=$(CONTAINER_NAME) \
	IMAGE=$(IMAGE) \
	PORT=$(PORT) \
	ENV_FILE=$(ENV_FILE) \
	envsubst < $(COMPOSE_TEMPLATE) > $(COMPOSE_FILE)
	@docker compose -f $(COMPOSE_FILE) up -d
	@#rm -f $(COMPOSE_FILE)
	@echo "Container $(CONTAINER_NAME) started."

# Stop and remove container and volume
clean:
	@echo "Cleaning up container: $(CONTAINER_NAME)"
	@docker compose -f $(COMPOSE_FILE) down -v || true
	@docker rm -f $(CONTAINER_NAME) || true
	@docker volume prune -f
	@rm -f $(COMPOSE_FILE)
	@echo "Cleanup complete."



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