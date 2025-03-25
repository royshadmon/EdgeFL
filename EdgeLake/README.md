# Deploying EdgeLake

EdgeLake provides Real-Time Visibility and Management of Distributed Edge Data, Applications and Infrastructure. EdgeLake 
transforms the edge to a scalable data tier that is optimized for IoT data, enabling organizations to extract real-time 
insight for any use case in any industries spanning Manufacturing, Utilities, Oil & Gas, Retail, Robotics, Smart Cities, 
Automotive, and more.

* [Documentation](https://edgelake.github.io/)
* [EdgeLake Source Code](https://github.com/EdgeLake/EdgeLake)
* [Surrounding components install](support.md)


## Prepare Machine
* [Docker & Docker-Compose](https://docs.docker.com/engine/install/)
* _Makefile_
```shell
sudo snap install docker
sudo apt-get -y install docker-compose 
sudo apt-get -y install make
 
# Grant non-root user permissions to use docker
USER=`whoami`
sudo groupadd docker 
sudo usermod -aG docker ${USER} 
newgrp docker
```

* Clone _docker-compose_ from EdgeLake repository
```shell
git clone https://github.com/EdgeLake/docker-compose
cd docker-compose
```

## Basic Deployment
EdgeLake deployment contains  predefined configurations for each node type, enabling users to deploy a network with a 
simple `docker run` command. This approach allows for quick deployment with minimal configuration but is limited to one 
node type per machine. To overcome this limitation, additional environment configurations can be provided.

### Default Deployment and Networking Configuration
When deploying using the basic command, the container utilizes the default parameters based on `NODE_TYPE`, with the 
following networking configurations:

<html>
<table>
   <tr>
      <th>Node Type</th>
      <th>Server Port</th>
      <th>Rest Port</th>
      <th>Run command</th>
   </tr>
   <tr>
      <td>Master</td>
      <td>32048</td>
      <td>32049</td>
      <td><code>docker run -it -d \ 
<br/>-p 32048:32048 \
<br/>-p 320498:32049 \
<br/>-e NODE_TYPE=master \
<br/>--name edgelake-master --rm anylogco/edgelake:latest</code></td>
   </tr>
   <tr>
      <td>Operator</td>
      <td>32148</td>
      <td>32149</td>
      <td><code>docker run -it -d \ 
<br/>-p 32148:32148 \
<br/>-p 32149:32149 \
<br/>-e NODE_TYPE=operator \
<br/>-e LEDGER_CONN=[MASTER_NODE IP:Port] \
<br/>--name edgelake-operator --rm anylogco/edgelake:latest</code></td>
   </tr>
   <tr>
      <td>Query</td>
      <td>32348</td>
      <td>32349</td>
      <td><code>docker run -it -d \ 
<br/>-p 32348:32348 \
<br/>-p 32349:32349 \
<br/>-e NODE_TYPE=query \
<br/>-e LEDGER_CONN=[MASTER_NODE IP:Port] \
<br/>--name edgelake-query --rm anylogco/edgelake:latest</code></td>
   </tr>
   <tr>
      <td>Generic</td>
      <td>3548</td>
      <td>32549</td>
      <td><code>docker run -it -d \ 
<br/>-p 32548:32548 \
<br/>-p 32549:32549 \
<br/>-e NODE_TYPE=generic \
<br/>--name edgelake-node --rm anylogco/edgelake:latest</code></td>
   </tr>
</table>
</html>


## Deploy EdgeLake via Docker
1. Update `.env` configurations for the node(s) being deployed -- Edit `LEDGER_CONN` in _query_ and _operator_ using  the 
IP address of master node
   * [docker_makefile/edgelake_master.env](docker_makefile/edgelake_master.env)
   * [docker_makefile/edgelake_operator.env](docker_makefile/edgelake_operator1.env)
   * [docker_makefile/edgelake_query.env](docker_makefile/edgelake_query.env)

2. Start Node using _makefile_
```shell
make up EDGELAKE_TYPE=[NODE_TYPE]
```

### Makefile Commands for Docker
```shell
Targets:
  build       Pull the docker image
  up          Start the containers
  attach      Attach to EdgeLake instance
  test        Using cURL validate node is running
  exec        Attach to shell interface for container
  down        Stop and remove the containers
  logs        View logs of the containers
  clean-vols  Stop and remove the containers and remove image and volumes
  clean       Stop and remove the containers and remove volumes 
  help        Show this help message
  supported EdgeLake types: generic, master, operator, and query
Sample calls: make up EDGELAKE_TYPE=master | make attach EDGELAKE_TYPE=master | make clean EDGELAKE_TYPE=master
```

## Advanced configurations
Provides a subset of the configurations required to deploy a node. A full list of the configurations can be found in
AnyLog's [Docker Compose repository](https://github.com/AnyLog-co/docker-compose/tree/main/docker-makefile). 

Configurations include:
* manually set geolocation 
* threading and pool sizes
* utilize live blockchain rather than master node
* [Overlay network](#overlay-network)
* [Deploying personalized scripts](https://github.com/AnyLog-co/documentation/blob/master/deployments/executing_scripts.md)

### Overlay Network
One of the things we offer a fully integrated connection to <a href="https://nebula.defined.net/docs" target="_blank">Nebula Overlay Network</a>.

* [Nebula - In General](https://github.com/AnyLog-co/documentation/blob/master/deployments/Networking%20%26%20Security/nebula.md)
* [Preparing for Nebula](https://github.com/AnyLog-co/documentation/blob/master/deployments/Networking%20%26%20Security/nebula_through_anylog.md)
* [Configuring Overlay Network](https://github.com/AnyLog-co/documentation/blob/master/deployments/Networking%20%26%20Security/Configuring%20Overlay%20with%20AnyLog.md)

To deploy, update configurations with the following params
```dotenv
# Overlay IP address - if set, will replace local IP address when connecting to network
OVERLAY_IP=""

# whether to enable Lighthouse
ENABLE_NEBULA=false
# create new nebula keys
NEBULA_NEW_KEYS=false
# whether node is type lighthouse
IS_LIGHTHOUSE=false
# Nebula CIDR IP address for itself - the IP component should be the same as the OVERLAY_IP (ex. 10.10.1.15/24)
CIDR_OVERLAY_ADDRESS=10.10.1.1/24
# Nebula IP address for Lighthouse node (ex. 10.10.1.15)
LIGHTHOUSE_IP=10.10.1.1
# External physical IP of the node associated with Nebula lighthouse
LIGHTHOUSE_NODE_IP=172.232.250.209
```

