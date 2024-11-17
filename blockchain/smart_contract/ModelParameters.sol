// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;

contract ModelParameters {

    // uint: round number
    // roundParams: metadata for the specific round
    mapping(uint => roundParams) roundMetaData;

    uint currentRoundNumber = 0;

    // struct defined for the metadata
    struct roundParams {
        // node parameters that have been added by nodes that can be accessed from the index of the node name from replicaNameToNodeIndex
        // replicaName -> mapped to -> index, this index then refers to a specific index in nodeParamsDownLoadLinks
        string[] nodeParamsDownLoadLinks;
        string initParamsDownloadLink; // initial params for the rounds
        mapping(string => uint) replicaNameToNodeIndex; // node name mapped to a node index
        string[] replicaNames; // node names
        uint minNumParams; // minimum number of parameters required by aggregator
    }

    // function to start new round of training
    function startRound(string memory initParamsDownloadLink, uint roundNumber, uint minNumParams) public {
        // check the current round
        require(currentRoundNumber + 1 == roundNumber, "Incorrect round number");

        // increment current round numbers
        currentRoundNumber += 1;

        // initialize this rounds initial params
        roundMetaData[roundNumber].initParamsDownloadLink = initParamsDownloadLink;

        // save the minimum amount of participation required by aggregator
        roundMetaData[roundNumber].minNumParams = minNumParams;

        // emit that a new round is starting
        emit newRound(roundNumber, initParamsDownloadLink);
    }

    // function to add model parameters trained by a node and emit the event to the aggregator that all nodes
    // have trained their local model parameters
    function addNodeParams(uint roundNumber, string memory newNodeParams, string memory replicaName) public {
        // check the current round
        require(currentRoundNumber == roundNumber, "Incorrect round number");

        // add the new node params to the list for node params for this round
        roundMetaData[roundNumber].nodeParamsDownLoadLinks.push(newNodeParams);

        // add the replica name to the list of names that have participated in this round
        roundMetaData[roundNumber].replicaNames.push(replicaName);

        // map the replica name to an index number generated from the length of the number of node params added to the list of node params
        // the length - 1 indicates the last node to have added its parameters to the list of node params, which serves as the index to
        // find that node's params in the node param list
        roundMetaData[roundNumber].replicaNameToNodeIndex[replicaName] = roundMetaData[roundNumber].nodeParamsDownLoadLinks.length - 1;

        // emit the number nodes that have added their node params to the list of node params so that aggregator can
        // check how many have participated
        if (roundMetaData[roundNumber].nodeParamsDownLoadLinks.length == roundMetaData[roundNumber].minNumParams) {
            emit updateAggregatorWithParamsFromNodes(roundMetaData[roundNumber].nodeParamsDownLoadLinks.length, roundMetaData[roundNumber].nodeParamsDownLoadLinks);
        }
    }

    // event to start a new round
    event newRound(uint roundNumber, string initParamsDownloadLink);

    // event to tell aggregator how many nodes participated
    event updateAggregatorWithParamsFromNodes(uint numberOfParams, string[] paramsFromNodes);

}
