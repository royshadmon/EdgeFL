# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the /edgefl contents into the container at current directories
COPY /edgefl .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Define environment variable
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Make port 8080 available to the world outside this container
EXPOSE ${PORT}

# Run aggregator_server.py when the container launches
CMD ["python", "app.py"]