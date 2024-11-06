import requests
import time
from flask import Flask, request, jsonify
import threading

# Test node server to receive data
app = Flask(__name__)
received_data = []

@app.route('/receive_data', methods=['POST'])
def receive_data():
    """Endpoint to receive data from data source"""
    data = request.json.get('data')
    if data:
        received_data.append(data)
        print(f"Features shape: {len(data['features'])}x{len(data['features'][0])}")
        print(f"Labels shape: {len(data['labels'])}")
        return jsonify({"status": "success", "message": "Data received"})
    return jsonify({"error": "No data provided"}), 400

def run_test_node():
    """Run the test node server"""
    app.run(host='0.0.0.0', port=8081)

def run_test_node2():
    """Run the test node server"""
    app.run(host='0.0.0.0', port=8085)

def test_data_source():
    """Test the data source functionality"""
    # Start test node server
    node_thread = threading.Thread(target=run_test_node)
    node_thread.daemon = True
    node_thread.start()
    time.sleep(2)  

    print("\nInitializing data source...")
    init_response = requests.post(
        'http://localhost:5002/init',  
        json={
            'node_urls': ['http://localhost:8081/'],
            'batch_size': 32 
        }
    )
    print(f"Initialization response: {init_response.json()}")

    try:
        while True:
            time.sleep(1)  # Keep alive, periodically print the status
            print("\nWaiting for data... Total batches received:", len(received_data))
    except KeyboardInterrupt:
        print("Test data source stopped.")

    # print("\nStarting data distribution test...")
    # for i in range(3):
    #     print(f"\nTriggering round {i+1}...")
    #     distribute_response = requests.post(
    #         'http://localhost:8082/distribute', 
    #         json={}
    #     )
    #     print(f"Distribution response: {distribute_response.json()}")
    #     time.sleep(2)  

    print("\nTest Summary:")
    print(f"Total batches received: {len(received_data)}")
    for i, batch in enumerate(received_data):
        print(f"\nBatch {i+1}:")
        # print(f"Round number: {batch['round']}")
        print(f"Number of samples: {len(batch['features'])}")
        print(f"Feature dimensionality: {len(batch['features'][0])}")
        print(f"Number of labels: {len(batch['labels'])}")

if __name__ == '__main__':
    test_data_source()