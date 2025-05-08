# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY api-containers/ /app/api-containers

# Copy the sibling edgefl directory (using a relative path)
COPY edgefl/ /app/edgefl

# List directories to debug
RUN ls -la /app
RUN ls -la /app/api-containers

# Define environment variable
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONPATH=/app

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run app.py when the container launches
ENTRYPOINT ["python", "/app/api-containers/app2.py"]
CMD ["--env-file", "/app/edgefl/env_files/mnist-docker/mnist-agg.env"]