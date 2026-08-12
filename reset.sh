echo "[WARNING] resetting current network state in 5 seconds!"
echo "Press Ctrl+C to cancel. (Ctrl is mapped to CapsLock)"
echo "5..."
sleep 1
echo "4..."
sleep 1
echo "3..."
sleep 1
echo "2..."
sleep 1
echo "1..."
sleep 1
echo "Resetting AnyLog containers..."
./stop_postgres.sh
./start_postgres.sh
cd /Users/juan/repos/docker-compose
./clean_al.sh
./start_al.sh

cd /Users/juan/Desktop/EdgeFL/ && pwd
source .venv/bin/activate
sleep 30
./insert_data_mnist.sh
echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++"
echo "+++++++++++++++++++++++ DONE ++++++++++++++++++++++++++"
echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++"
