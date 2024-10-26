// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;

contract ModelParameters {

    // model parameters coming in from each node
    uint[][] nodeParams;

    // model parameters coming from aggregator
    uint[] aggregatorParams;

    // address of the aggregator (contract deployer)
    address public Aggregator;

    // list of predifined node addresses for training
    address[] public Nodes;

    // constructor called upon at deployment of contract by aggregator server
    constructor(address[] memory nodes) {
        Aggregator = msg.sender;
        Nodes = nodes;
    }

    // event emitted to nodes with updated model params from aggregator
    event updateNode(uint[] updatedParams);

    // event emitted to aggregator with newly trained model params from nodes
    event updateAgg(uint[][] nodeParams); 

    // event emitted to nodes to initally start training
    event startTraining();

    // function to add a new node if the list of nodes used for training needs to be updated
    function addNode(address newNode) public {
        require(msg.sender == Aggregator);
        Nodes.push(newNode);
    }

    // function to update aggregator model parameters, reset node model parameters, and then send event 
    // to nodes listening that model paramters have been updated from the aggregator
    function updateParams(uint[] memory newParams, bool updateNodes) public {
        require(msg.sender == Aggregator);
        aggregatorParams = newParams;
        delete nodeParams;
        if (updateNodes) {
            emit updateNode(aggregatorParams);
        }
    }

    // function to add model paramters trained by a node and emit the event to the aggregator that all nodes
    // have trained their local model paramaters
    function addNodeParams(uint[] memory newNodeParams) public {
        require(isSenderAllowed(msg.sender));
        nodeParams.push(newNodeParams);
        if (nodeParams.length == Nodes.length) {
            emit updateAgg(nodeParams);
        }
    }

    // Internal function to check if an address is in the predefined list of nodes
    function isSenderAllowed(address _sender) internal view returns (bool) {
        for (uint i = 0; i < Nodes.length; i++) {
            if (Nodes[i] == _sender) {
                return true;
            }
        }
        return false;
    }

    // function to emit the event that will trigger all the nodes to initially start training
    function initTraining() public {
        require(msg.sender == Aggregator);
        emit startTraining();
    }

}
