#!/bin/bash

# Set the UID and GID for the user
USER_ID=${UID:-99}
GROUP_ID=${GID:-100}

echo "Starting with UID: $USER_ID, GID: $GROUP_ID"

# Create a new user and group with the specified UID and GID
groupadd -g $GROUP_ID -o usergroup
useradd -m -u $USER_ID -g $GROUP_ID -o -s /bin/bash user

# Set ownership and permissions
chown -R $USER_ID:$GROUP_ID /home/user
chown -R $USER_ID:$GROUP_ID /usr/src/app

# Set ownership and group for the database target folder

DATABASE_FOLDER=${FOLDER:-/database}
chown -R $USER_ID:$GROUP_ID $DATABASE_FOLDER

# Set the desired umask
UMASK_VALUE=${UMASK:-0022}
umask $UMASK_VALUE

# Run the Python script using pipenv as the specified user
su user -c "python /usr/src/app/main.py"
