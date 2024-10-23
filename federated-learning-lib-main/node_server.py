from flask import Flask, request, jsonify
import numpy as np
from ibmfl.party.training.local_training_handler import LocalTrainingHandler
from ibmfl.connection.flask_connection import FlaskConnection
import sys

app = Flask(__name__)

data_batches = []
local_training_handler = None
flask_connection = None

'''
/init [POST]
    - Endpoint to receive configuration from the aggregator
    - Initializes Local Training Handler and Flask Connection
'''
@app.route('/init', methods=['POST'])
def init():
    global local_training_handler, flask_connection
    
    config = request.json

    fl_model = config['model']['path']
    data_handler = config['data']['path'] 
    local_training_handler = LocalTrainingHandler(fl_model=fl_model, data_handler=data_handler)

    connection_config = {
        'ip': config['connection']['info']['ip'],
        'port': config['connection']['info']['port'],
        'tls_config': config['connection']['info']['tls_config'],
    }
    flask_connection = FlaskConnection(connection_config)
    flask_connection.initialize()

    return jsonify({"status": "config_set", "message": "Configuration received and initialized."})

'''
/receive_data [POST] (data)
    - Endpoint to receive data block from the aggregator
'''
@app.route('/receive_data', methods=['POST'])
def receive_data():
    # Assumes we get the data in correct format for specific DataHandler
    data = request.json.get('data')
    if data:
        data_batches.append((np.array(data)))
        return jsonify({"status": "data_received", "batch_size": len(data)})
    return jsonify({"error": "No data provided"}), 400


'''
/training_round [POST]
    - Endpoint to start a training round
    - Returns updated model parameters
'''
@app.route('/training_round', methods=['POST'])
def training_round():
    if not data_batches:
        return jsonify({"error": "No data to train on"}), 400
    data = data_batches.pop(0)
    # Assumes we have load_data method (not on API online)
    local_training_handler.data_handler.load_data(data)
    model_update = local_training_handler.train()
    return jsonify({"status": "training_complete", "model_update": str(model_update)})

'''
/kill [POST]
    - Kills Flask Connection to server
'''
@app.route('/kill', methods=['POST'])
def kill():
    if not flask_connection:
        return jsonify({"error": "No flask connection to aggregator"}), 400
    flask_connection.stop()
    flask_connection = None
    return jsonify({"status": "party connection removed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
