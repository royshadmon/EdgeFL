#!/bin/zsh

cd EdgeLake/postgres

echo "+++++++++++++++ Starting postgres containers +++++++++++++++"
echo "Container postgres1..."
make up NAME=postgres1 HOST_PORT=5432 VOLUME=pgdata1
echo "Container postgres2..."
make up NAME=postgres2 HOST_PORT=5433 VOLUME=pgdata2
echo "Container postgres3..."
make up NAME=postgres3 HOST_PORT=5434 VOLUME=pgdata3
cd ../..
