#!/bin/bash

# Variables - comma separated host:port list
DB_HOSTS="192.168.1.125:5432,192.168.1.125:5433,192.168.1.125:5434"
#DB_HOSTS="192.168.1.125:5433"
DB_NAME="mnist_fl"
DB_USER="demo"

# Prompt for password (you can also export PGPASSWORD before running the script)
#echo -n "Enter password for user $DB_USER: "
#read -s PGPASSWORD
#export PGPASSWORD
#echo

PGPASSWORD="passwd"

# Convert the comma-separated list into an array
IFS=',' read -ra HOST_PORT_ARRAY <<< "$DB_HOSTS"

# Loop over each host:port pair
for HOST_PORT in "${HOST_PORT_ARRAY[@]}"; do
    HOST="${HOST_PORT%%:*}"   # Extract host (before :)
    PORT="${HOST_PORT##*:}"   # Extract port (after :)

    echo "Connecting to $HOST:$PORT ..."

    # Fetch all table names from public schema
    TABLES=$(PGPASSWORD="$PGPASSWORD" psql -h "$HOST" -p "$PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT tablename FROM pg_tables WHERE schemaname = 'public';")

    # Drop each table
    for TABLE in $TABLES; do
        echo "Dropping table: $TABLE on $HOST:$PORT"
        PGPASSWORD="$PGPASSWORD" psql -h "$HOST" -p "$PORT" -U "$DB_USER" -d "$DB_NAME" \
          -c "DROP TABLE IF EXISTS \"$TABLE\" CASCADE;"
    done

    echo "Finished dropping tables on $HOST:$PORT"
done

unset PGPASSWORD
echo "All done."
