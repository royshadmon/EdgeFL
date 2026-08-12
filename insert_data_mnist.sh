#!/bin/zsh

cd /Users/juan/Desktop/EdgeFL/edgefl/data/mnist

echo "INSERTING INTO NODE 1"
PYTHONUNBUFFERED=1 python3.11 store_data.py 127.0.0.1:32149 --db-name mnist_fl
echo "INSERTING INTO NODE 2"
PYTHONUNBUFFERED=1 python3.11 store_data.py 127.0.0.1:32249 --db-name mnist_fl
echo "INSERTING INTO NODE 3"
PYTHONUNBUFFERED=1 python3.11 store_data.py 127.0.0.1:32349 --db-name mnist_fl
