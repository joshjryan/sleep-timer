# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5553 available to the world outside this container
EXPOSE 5553

# Copy the .env file into the container
#COPY .env .env

# Run app.py when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:5553", "app:app"]
