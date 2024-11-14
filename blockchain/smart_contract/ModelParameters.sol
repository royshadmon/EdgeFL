// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;

contract ModelParameters {

    // uint: round number
    // roundParams: metadata for the specific round
    mapping(uint => roundParams) roundMetaData;

    uint currentRoundNumber = 0;

    // struct to store a node's split parameters
    struct nodeParams {
        string[] spiltNodeParam;
    }

    // struct defined for the metadata
    struct roundParams {
        // node parameters that have been added by nodes that can be accessed from the index of the node name from replicaNameToNodeParams
        // replicaName -> mapped to -> index, this index then refers to a specific index in nodeParams
        // string[] nodeParams;
        string initParams; // initial params for the rounds
        mapping(string => nodeParams) replicaNameToNodeParams; // replica name mapped to a node params struct
        mapping(string => bool) replicaNamesExists; // map replica names to a boolean to check if they exist
        string[] replicaNames; // Iterable data structure storing keys for replicaNameToNodeParams of nodes that have participated
        uint minNumParams; // minimum number of parameters required by aggregator
    }

    // function to start new round of training
    function startRound(string memory initParams, uint roundNumber, uint minNumParams) public {
        // check the current round
        require(currentRoundNumber + 1 == roundNumber, "Incorrect round number");

        // increment current round numbers
        currentRoundNumber += 1;

        // initialize this rounds initial params
        roundMetaData[roundNumber].initParams = initParams;

        // save the minimum amount of participation required by aggregator
        roundMetaData[roundNumber].minNumParams = minNumParams;

        // emit that a new round is starting
        emit newRound(roundNumber, initParams);
    }

    // function to add segment of model parameters trained by a node and emit the event to the aggregator that all nodes
    // have trained their local model parameters
    // NOTE:
    // have to iterate through all the node parameter segments and emit each one individually because we can't emit
    // the entire string[] which contains all the segments since it could give us the same timeout error because it's too large
    function addNodeParams(uint roundNumber, string memory newNodeParams, string memory replicaName, bool finishNode) public {
        // check the current round
        require(currentRoundNumber == roundNumber, "Incorrect round number");

        // add the new node params to the array of split node params in the node params struct for a specific node
        roundMetaData[roundNumber].replicaNameToNodeParams[replicaName].spiltNodeParam.push(newNodeParams);

        // if all of nodes segments have been uploaded
        if (finishNode) {
            // check if the replica name doesn't exists in the list already
            if (!roundMetaData[roundNumber].replicaNamesExists[replicaName]) {
                // add the new replica name to the map indicating that it exists
                roundMetaData[roundNumber].replicaNamesExists[replicaName] = true;

                // add the new replica name to the list that keeps track of the keys
                roundMetaData[roundNumber].replicaNames.push(replicaName);
            }
        }

        // first value emitted is the number nodes that have participated
        // second value emitted is a node parameter segment
        if (roundMetaData[roundNumber].replicaNames.length == roundMetaData[roundNumber].minNumParams) {

            // iterate through the replicas that have participated
            for (uint i = 0; i < roundMetaData[roundNumber].replicaNames.length; i++) {
                // gather the name from the list
                string memory name = roundMetaData[roundNumber].replicaNames[i];

                // itertate through the split up node params for a replica name
                for (uint j = 0; i < roundMetaData[roundNumber].replicaNameToNodeParams[name].spiltNodeParam.length; j++) {
                    // gather the node paramater segment
                    string memory nodeParamsSegment = roundMetaData[roundNumber].replicaNameToNodeParams[name].spiltNodeParam[j];

                    // emit the event with the number of nodes that participated, node name, and node parameter segment
                    emit updateAggregatorWithParamsFromNodes(roundMetaData[roundNumber].replicaNames.length, name, nodeParamsSegment);
                }
            }
        }



    }

    // event to start a new round
    event newRound(uint roundNumber, string initParams);

    // event to tell aggregator how many nodes participated and the trained parameters from the nodes
    event updateAggregatorWithParamsFromNodes(uint numberOfNodes, string replicaName, string paramsFromNodes);

}
