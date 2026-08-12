#!/bin/zsh

cd EdgeLake/postgres

echo "+++++++++++++++ Shutting down postgres containers +++++++++++++++"
echo "Container postgres1"
make clean NAME=postgres1
echo "Container postgres2"
make clean NAME=postgres2
echo "Container postgres3"
make clean NAME=postgres3
