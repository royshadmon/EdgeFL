# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
#### Ask Roy about options ####

# Option 1: Add all of /platform_components to the container
#       COPY /platform_components /app

# Option 2: Add only Aggregator folder and necessary files to the container
#       COPY /platform_components/aggregator /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Define environment variable
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Make port 8080 available to the world outside this container
EXPOSE ${PORT}

# Run aggregator_server.py when the container launches
CMD ["sh", "-c", "uvicorn aggregator_server:app --reload --host 0.0.0.0 --port ${PORT}"]