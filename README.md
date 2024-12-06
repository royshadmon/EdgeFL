# EdgeLake Project

<!-- To Do

- Need to add different commands for Mac & Windows
  -->

## Why EdgeLake:

 **Efficiency:**  Reduces data transfer by sharing model parameters instead of sharing entire datasets.

- **Performance:** Our distributed system enables high-computation training to be split across multiple nodes, significantly enhancing speed and scalability compared to single-node processing. .

- **Privacy:** Keeps data on nodes, minimizing exposure risks and enhancing security with privacy-preserving technologies such as blockchain.


## Prerequisites
<!-- we need specifiy more stuff here -->
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

---

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

---
