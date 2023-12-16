# Use an official Python runtime as a parent image
FROM python:3.12-bookworm

# Set the working directory in the container
WORKDIR /usr/src/app

# Install pipenv
RUN pip install pipenv

# Copy the Pipfile and Pipfile.lock into the container at /usr/src/app
COPY Pipfile Pipfile.lock ./

# Install dependencies using pipenv
# --system flag installs dependencies system-wide, avoiding virtualenv
RUN pipenv install --deploy --system --ignore-pipfile

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Make the entrypoint script executable
RUN chmod +x /usr/src/app/entrypoint.sh

# Run the application
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]