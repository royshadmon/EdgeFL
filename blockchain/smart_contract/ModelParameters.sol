// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;

contract ModelParameters {

    // uint: round number
    // roundParams: metadata for the specific round
    mapping(uint => roundParams) roundMetaData;

    mapping(uint => mapping(string=>bool)) public hasSubmittedParams; //this mapping will check if the node has submmitted params for the specific round
    uint currentRoundNumber = 0;
    
    // struct defined for the metadata
    struct roundParams {
        // node parameters that have been added by nodes that can be accessed from the index of the node name from replicaNameToNodeIndex
        // replicaName -> mapped to -> index, this index then refers to a specific index in nodeParams
        string[] nodeParams; //use this to keep track of nodes added
        string initParams; // initial params for the rounds
        string aggregatorParams;  // aggregator params which serve as init params for the next round
        mapping(string => uint) replicaNameToNodeIndex; // node name mapped to a node index
        string[] replicaNames; // node names
        uint minParams;
    }

    // function to start new round of training
    function startRound(string memory initParams, uint roundNumber, uint minParams) public {
        // check the current round
        require(currentRoundNumber + 1 == roundNumber, "Incorrect round number");

        // increment current round numbers
        currentRoundNumber += 1;

        // initialize this rounds initial params
        roundMetaData[roundNumber].initParams = initParams;

        roundMetaData[roundNumber].minParams = minParams;

        // emit that a new round is starting
        emit newRound(roundNumber, initParams);
    }

    // function to add model parameters trained by a node and emit the event to the aggregator that all nodes
    // have trained their local model parameters
    function addNodeParams(uint roundNumber, string memory newNodeParams, string memory replicaName) public isCurrentRound(roundNumber) {
        //check that duplicate param submission for the round will not occur, if it already sent, a duplicate is trying to be sent so it will be cancelled 
        require(!hasSubmittedParams[roundNumber][replicaName], "Node already submitted parameters for this round");
        
        //if it wasnt a duplicate submission, we set that the param submission has occured, if something failed in the contract, these flags would be reverted anyway
        hasSubmittedParams[roundNumber][replicaName] = true;

        // add the new node params to the list for node params for this round
        roundMetaData[roundNumber].nodeParams.push(newNodeParams);

        // add the replica name to the list of names that have participated in this round
        roundMetaData[roundNumber].replicaNames.push(replicaName);

        // map the replica name to an index number generated from the length of the number of node params added to the list of node params
        // the length - 1 indicates the last node to have added its parameters to the list of node params, which serves as the index to
        // find that node's params in the node param list
        roundMetaData[roundNumber].replicaNameToNodeIndex[replicaName] = roundMetaData[roundNumber].nodeParams.length - 1;

        
        // emit the number nodes that have added their node params to the list of node params so that aggregator can
        // check how many have participated
        //make sure this is only done after isRoundComplete is True
        bool roundCompleteFLag = isRoundComplete(roundMetaData[roundNumber].nodeParams.length, roundMetaData[roundNumber].minParams);
        if (roundCompleteFLag == true){
            emit updateAggregatorWithParamsFromNodes(roundMetaData[roundNumber].nodeParams.length, roundMetaData[roundNumber].nodeParams);
        }
    }


    // function to update aggregator model parameters and then send event
    // to nodes listening that model paramters have been updated from the aggregator
    function updateParams(uint roundNumber, string memory newParamsFromAggregator) public isCurrentRound(roundNumber) {
        // update the aggregator params for this round
        roundMetaData[roundNumber].aggregatorParams = newParamsFromAggregator;

//        // emit the new aggregator params to all the nodes
//        emit updateNodesWithParamsFromAggregator(roundMetaData[roundNumber].aggregatorParams);

    }
    

    function isRoundComplete(uint numParams, uint minParams) returns(bool) {
        //TODO implement logic for a timeout or a percentage at minimum with timeout
        return numParams == minParams;
    }

    modifier isCurrentRound(uint roundNumber){
        require(currentRoundNumber == roundNumber, "Incorrect round number");
        _; //this makes it jump to the main body code
    }

    // event to start a new round
    event newRound(uint roundNumber, string initParams);

    // event to tell aggregator how many nodes participated
    event updateAggregatorWithParamsFromNodes(uint numberOfParams, string[] paramsFromNodes);

//    // event to update nodes with new parameters from aggregator
//    event updateNodesWithParamsFromAggregator(string newAggregatorParams);


}
