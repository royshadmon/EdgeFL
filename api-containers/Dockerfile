# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the /edgefl contents into the container at current directories
COPY /edgefl /app/edgefl
COPY /api-containers /app/api-containers
COPY /requirements.txt /app/requirements.txt


# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Define environment variable
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONPATH=/app

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run aggregator_server.py when the container launches
ENTRYPOINT ["python", "/app/api-containers/app2.py", "--env-file"]
CMD ["/app/edgefl/env_files/mnist/mnist-agg.env"]