# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY api-containers/app.py /app/api-containers/app.py

# Copy the sibling edgefl directory (using a relative path)
COPY edgefl/platform_components /app/edgefl/platform_components

COPY edgefl/env_files /app/edgefl

# List directories to debug
RUN ls -la /app
#RUN ls -la /app/api-containers

# Define environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app