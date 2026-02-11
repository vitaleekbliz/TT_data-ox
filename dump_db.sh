#!/bin/bash
# Configuration passed from Python or environment
CONTAINER_NAME=${1:-db}
DB_USER=${2:-my_user}
DB_NAME=${3:-app_db}
DUMP_DIR="./dumps"

mkdir -p $DUMP_DIR
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
FILENAME="${DUMP_DIR}/backup_${TIMESTAMP}.sql.gz"

# Stream dump from Docker -> Gzip -> Local File
# We use the -t flag for docker exec to ensure a pseudo-TTY if needed
docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME | gzip > $FILENAME

echo "$FILENAME"