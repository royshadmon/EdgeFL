from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import torch
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from torch.utils.data import TensorDataset, DataLoader
import kagglehub
import os
import requests
import time
import threading
from threading import Event


app = Flask(__name__)


class DataSource:
    def __init__(self, num_parties, batch_size=32): # number of nodes, batch size, number of rounds are configurable
        self.num_parties = num_parties
        self.batch_size = batch_size

        self.node_urls = []
        self.party_dataloaders = []
        self.is_running = False            # data distribution  in each round by the aggregator
        self.prepare_smoking_data()


    '''Prepares the smoking dataset for federated learning
       by splitting the data into multiple datasets for each node
    '''
    def prepare_smoking_data(self):
        # Download dataset from Kaggle
        dataset_path = kagglehub.dataset_download("wonghoitin/datasets-for-federated-learning")
        data_path = os.path.join(dataset_path, 'wefe-default_data', 'smoking', 'smoking.csv')
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Smoking dataset not found at {data_path}")
        
        # Load and preprocess the dataset
        data = pd.read_csv(data_path)
        columns = data.select_dtypes(include=['object']).columns
        label_encoders = {}
        for column in columns:
            label_encoders[column] = LabelEncoder()
            data[column] = label_encoders[column].fit_transform(data[column])
        
        X = data.drop('smoking', axis=1)
        y = data['smoking']
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Split the data for each party
        test_size = 1 - 1/self.num_parties if self.num_parties > 1 else 0.25
        for _ in range(self.num_parties):
            X_party, X_temp, y_party, y_temp = train_test_split(
                X_scaled, y, 
                test_size=test_size, 
                stratify=y
            )
            # Create TensorDataset
            X_tensor = torch.FloatTensor(X_party)
            y_tensor = torch.LongTensor(y_party.values)
            dataset = TensorDataset(X_tensor, y_tensor)
            
            # Create DataLoader with batch_size
            dataloader = DataLoader(
                dataset, 
                batch_size=self.batch_size, 
                shuffle=True,
                drop_last = True # do not pad the final batch if it's a little small
            )
            self.party_dataloaders.append(dataloader)
            X_scaled, y = X_temp, y_temp

        print(f"Data split into {self.num_parties} parties with batch size {self.batch_size}")

    def distribute_data(self):
        """Distribute the next batch of data to each node"""
        distribution_results = []

        max_batches = [len(dataloader) for dataloader in self.party_dataloaders]
        print('max batches per node, ', max_batches)

        node_iterators = [iter(dataloader) for dataloader in self.party_dataloaders]
        while any(node_iterators):
            for node_idx, (node_url, dataloader_iterator) in enumerate(zip(self.node_urls, node_iterators)):
                try:
                    if dataloader_iterator is None:
                        continue

                    # Get next batch
                    batch = next(dataloader_iterator)

                    X_batch, y_batch = batch
                    
                    # Convert to numpy and then to list for JSON serialization
                    data_batch = {
                        'features': X_batch.numpy().tolist(),
                        'labels': y_batch.numpy().tolist(),
                    }
                    

                    # Send data to node
                    response = requests.post(
                        f'{node_url}/receive_data',
                        json={
                            'data': data_batch,
                            'node_id': node_idx,
                            'round': 1
                        }  
                    )

                    distribution_results.append({
                        'node_idx': node_idx,
                        'success': response.status_code == 200,
                        'message': response.text if response.status_code != 200 else "Success"
                    })

                    

                    if response.status_code == 200 or response.status_code == 201:
                        print(f"Successfully sent batch to node {node_idx}")
                    else:
                        print(f"Failed to send batch to node {node_idx}: {response.text}")


                except StopIteration: # if iterator runs out of data
                    # Set the iterator to None when finished
                    node_iterators[node_idx] = None
                    print(f"No more data to distribute to node {node_idx}")
                except Exception as e:
                    error_msg = str(e)
                    print(f"Error distributing data to node {node_idx}: {error_msg}")
                    distribution_results.append({
                        'node_idx': node_idx,
                        'success': False,
                        'message': error_msg
                    })

        return distribution_results

    def start_distribution(self):
        """Start the data distribution process"""
        def distribution_loop():
            time.sleep(5)
            self.is_running = True
            while self.is_running:
                
                # Distribute data
                if self.is_running:  # Check again in case stop was called while waiting
                    self.distribute_data()
                
                time.sleep(2)
                
            print("Data distribution completed")
            self.is_running = False

        thread = threading.Thread(target=distribution_loop)
        thread.start()

    def stop_distribution(self):
        """Stop the distribution process"""
        self.is_running = False
        self.distribution_event.set()  # Set event to unblock any waiting thread

# Initialize DataSource instance
data_source = None


'''
curl -X POST http://localhost:5002/init \-H "Content-Type: applica
tion/json" \-d '{    "node_urls": ["http://localhost:8081/"],    "ba
tch_size": 32}'
'''

@app.route('/init', methods=['POST'])
def initialize():
    """Initialize the data source with node information
    JSON body for request:
        node_urls: list of URLs for each node (required)
        batch_size: batch size for each node (default 32)
    """
    global data_source
    try:
        data = request.json
        num_parties = len(data['node_urls'])
        batch_size = data.get('batch_size', 32)

        data_source = DataSource(num_parties, batch_size)
        data_source.node_urls = data['node_urls']

        time.sleep(5)

        # Start data distribution
        data_source.start_distribution()

        return jsonify({
            'status': 'success',
            'message': f'DataSource initialized with {num_parties} nodes'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500




if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5002))
    app.run(host='0.0.0.0', port=port)