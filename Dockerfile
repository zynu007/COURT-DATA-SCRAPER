# Use the official Playwright Python image as a base.
# This image already contains all the necessary system dependencies and browsers.
# It's based on Ubuntu and is the most reliable way to run Playwright in a container.
FROM mcr.microsoft.com/playwright/python:latest

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container.
# It's best practice to copy this first to leverage Docker's build cache.
# This means if only the application code changes, this step doesn't need to be rerun.
COPY backend/requirements.txt .

# Install the Python dependencies listed in requirements.txt.
# We're using --no-cache-dir to prevent pip from storing cache data,
# which helps reduce the final image size.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files from your local 'backend' directory
# into the '/app' directory inside the container.
# The 'backend/' prefix is crucial here to specify the source directory on your host machine.
COPY backend .

# Expose port 5000 for the Flask application.
EXPOSE 5000

# Specify the command to run the application when the container starts.
# We use Gunicorn to run the Flask app, binding it to all network interfaces (0.0.0.0)
# on port 5000. This makes the app accessible from outside the container.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
