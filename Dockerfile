# Use an official Python runtime as a parent image
FROM python:3.12-alpine

# Set the working directory in the container
WORKDIR /usr/src/app

# Install pipenv
RUN pip install pipenv

# Copy the Pipfile and Pipfile.lock into the container at /usr/src/app
COPY Pipfile Pipfile.lock ./

# Install dependencies using pipenv
# --system flag installs dependencies system-wide, avoiding virtualenv
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --ignore-pipfile

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Set user to 99 and group to 100
RUN chown -R 99:100 /usr/src/app

# Run the program as above given user
USER 99:100

# Run the application
CMD ["pipenv", "run", "python", "./main.py"]