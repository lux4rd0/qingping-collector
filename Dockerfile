# Use the official Python image as the base image
FROM python:3.12.6-slim

# Set the working directory in the container
WORKDIR /app

# Update the OS and install necessary packages
RUN apt-get update && \
    apt-get install -y vim && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Optional: Upgrade pip to the latest version for better dependency handling and performance
RUN python -m pip install --upgrade pip

# Copy the requirements.txt file to the container
COPY requirements.txt /app/

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./src/app /app/
