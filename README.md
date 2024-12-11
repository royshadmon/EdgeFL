# Federated Learning -- AnyLog EdgeLake


<!-- To Do

- Need to add different commands for Mac & Windows
  -->

## Why EdgeLake:

 **Efficiency:**  Reduces data transfer by sharing model parameters instead of sharing entire datasets.

- **Performance:** Our distributed system enables high-computation training to be split across multiple nodes, significantly enhancing speed and scalability compared to single-node processing. .

- **Privacy:** Keeps data on nodes, minimizing exposure risks and enhancing security with privacy-preserving technologies such as blockchain.


## Prerequisites
<!-- we need specifiy more stuff here -->

- pip install -r requirements.txt
### Software Requirements
- Python 3.7+ installed.

### Repository Access
Clone the EdgeLake repository:
```bash
git clone https://github.com/EdgeLake/EdgeLake
```

### Files to Prepare
<!-- TODO: could prepare one and have users just update keys or write a script for this-->
- **master.env**: Ensure this file is available for configuration.                   
- **start-script.al**: This script is necessary for proper configuration.  
- **Example CURL commands file**: Keep this handy for testing and reference.
- **/blockchain/.env**: Used to specify system variables, file paths, etc. Update with values corresponding to your system.

---
<!-- I don't think we should do py charm -->
## Setup Instructions

### Step 1: Open the Project
- Open PyCharm and load the cloned EdgeLake repository.

### Step 2: Run Initial Setup
- Locate the file `edgelake.py` within the `edge_lake` directory in PyCharm.
- Click on the file and press **Run**. Allow the file to execute and then stop the run.

### Step 3: Edit Configuration
- Navigate to **Run > Edit Configurations** in PyCharm.
- Perform the following edits:
  
  #### 1. Paths to .env files:
  - Add the path to the `master.env` file in the appropriate section.
  - Open `master.env` and modify the `IP address` and `RPC provider` to match your environment.

  #### 2. Script Parameters:
  - Add the command below to the `Script parameters` section:
    ```bash
    process [path_to]/CSE-115D-start-script.al
    ```
    Replace `[path_to]` with the actual file path to `start-script.al`.

### Step 4: Run EdgeLake


### Step 5: Testing with CURL Commands
<!-- Example curl commands here -->


'''
CURL REQUEST FOR DEPLOYING CONTRACT-- General Form

curl -X POST http://localhost:[AGGREGATOR_PORT]/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:[NODE_0_PORT]",
    "http://localhost:[NODE_1_PORT]"
  ],
  "model_path": "[FILE_PATH_TO_PYTORCH_MODEL_SOURCE_CODE]",
  "model_init_params": [OPTIONAL, IF YOUR PYTORCH MODEL HAS ANY],
  "model_name": "[MODEL_NAME]",
  "model_weights_path": "[WHERE YOU WANT MODEL WEIGHTS SAVED]",
  "data_handler_path": "[FILE_PATH_TO_DATA_HANDLER_SOURCE_CODE]",
  "data_config": {"data": ["[DATA_FILE_FOR_NODE_0]",
                           "[DATA_FILE_FOR_NODE_1]]}
}'
'''


'''
CURL REQUEST FOR DEPLOYING CONTRACT-- custom dataset and model, 1 node 

curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081"
  ],
  "model_path": "C:\\Users\\nehab\\cse115d\\testmodel.py",
  "model_init_params": { "module__input_dim": 14 },
  "model_name": "custom_test",
  "model_weights_path": "C:\\Users\\nehab\\cse115d\\model_weights.pt",
  "data_handler_path": "C:\\Users\\nehab\\cse115d_anylog_edgelake\\custom_data_handler.py",
  "data_config": {"data": ["C:\\Users\\nehab\\cse115d_anylog_edgelake\\heart_data\\party_data\\party_0.csv"]}

}'
'''

'''
CURL REQUEST FOR DEPLOYING CONTRACT-- custom dataset and model, 2 nodes

curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081",
    "http://localhost:8082"
  ],
  "model_path": "C:\\Users\\nehab\\cse115d\\testmodel.py",
  "model_init_params": { "module__input_dim": 14 },
  "model_name": "custom_test",
  "model_weights_path": "C:\\Users\\nehab\\cse115d\\model_weights.pt",
  "data_handler_path": "C:\\Users\\nehab\\cse115d_anylog_edgelake\\custom_data_handler.py",
  "data_config": {"data": ["C:\\Users\\nehab\\cse115d_anylog_edgelake\\heart_data\\party_data\\party_0.csv",
                           "C:\\Users\\nehab\\cse115d_anylog_edgelake\\heart_data\\party_data\\party_1.csv"]}
}'
'''

'''
CURL REQUEST FOR DEPLOYING CONTRACT-- mnist built in dataset and model, 2 nodes

curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081",
    "http://localhost:8082"
  ],
  "model_path": "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\federated-learning-lib-main\\examples\\iter_avg\\model_pytorch.py",
  "model_name": "mnist_test",
  "model_weights_path": "C:\\Users\\nehab\\cse115d\\model_weights.pt",
  "data_handler_path": "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\venv38\\Lib\\site-packages\\ibmfl\\util\\data_handlers\\mnist_pytorch_data_handler.py",
  "data_config": {
    "npz_file": [
      "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\data\\mnist\\data_party0.npz",
      "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\data\\mnist\\data_party1.npz"
    ]
  }
}'
'''

'''
CURL REQUEST FOR DEPLOYING CONTRACT-- mnist dataset and sql model, 2 nodes

curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081",
    "http://localhost:8082"
  ],
  "model_path": "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\federated-learning-lib-main\\examples\\iter_avg\\model_pytorch.py",
  "model_name": "mnist_test",
  "model_weights_path": "C:\\Users\\nehab\\cse115d\\model_weights.pt",
  "data_handler_path": "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\custom_sql_datahandler.py",
  "data_config": {
    "npz_file": [
      "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\data\\mnist\\data_party0.npz",
      "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\data\\mnist\\data_party1.npz"
    ]
  }
}'
'''


## Automating CURL Commands
<!-- write a script at the end when all the code is ready -->

```python
import subprocess

# Define CURL commands
curl_commands = [
    "curl -X POST -H 'Content-Type: application/json' -d '{\"key\": \"value\"}' http://127.0.0.1:5000/api",
    "curl -X GET http://127.0.0.1:5000/api/status",
    # Add more commands here...
]

# Execute each command
for cmd in curl_commands:
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Command: {cmd}\nOutput:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {cmd}\nError:\n{e.stderr}")
```

### Instructions for Script



---

## Troubleshooting

### CLI Issues


### CURL Issues
- If CURL commands fail:
  - Verify the EdgeLake service is running.
  - Check network connectivity and server status.

