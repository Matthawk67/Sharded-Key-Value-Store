# kvsShard file

from flask import Flask, request
from flask_restful import Resource
from invalidUsage import InvalidUsage
import appdata
import json
from RequestHelper import getShardIDMembers, getShardIDKeyCount, getShardIDs, boot, sendRequest, findShard

# App resources.


class nodeShardID(Resource):
    def get(self):
        response = {'message': "Shard ID of the node retrieved successfully",
                    'shard-id': str(appdata.shardID)}
        return response, 200


class kvsShardIDs(Resource):
    def get(self):
        shardIDs = getShardIDs()
        response = {'message': "Shard IDs retrieved successfully",
                    'shard-ids': ",".join(str(ID) for ID in sorted(shardIDs))}
        return response, 200


class shardIDMembers(Resource):
    def get(self, shardID):
        members = getShardIDMembers(shardID)
        response = {'message': "Members of shard ID retrieved successfully",
                    'shard-id-members': ",".join(str(m) for m in members)}
        return response, 200


class shardIDKeyCount(Resource):
    def get(self, shardID):
        keyCount = getShardIDKeyCount(shardID)
        response = {'message': "Key count of shard ID retrieved successfully",
                    'shard-id-key-count': str(keyCount)}
        return response, 200


class addMember(Resource):
    def put(self, shardID):
        data = json.loads(request.data)
        SA = data['socket-address']
        respondToReshard = True if 'kvs' in data else False

        if SA != appdata.SOCKET_ADDRESS:
            endpoint = "/key-value-store-shard/add-member/" + str(shardID)
            nodeResponse = sendRequest("PUT", SA, endpoint, request.data)
            return nodeResponse.data, nodeResponse.status

        if respondToReshard:
            appdata.shardID = shardID
            appdata.kvs = data['kvs']
            appdata.SHARD_COUNT = data['shard-count']
            response = {"message": "migrated to shard " + str(shardID)}
            return response, 201

        # check if the shardID is existent
        shardIDs = getShardIDs()
        if str(shardID) not in shardIDs and 'kvs' in data:
            response = {"message": "Trying to add to nonexistent shard"}
            return response, 401

        # check if we don't already have a shardID
        if appdata.shardID == 'None':
            print("My shardID is none", flush=True)
            appdata.shardID = shardID
            boot()
            response = {'message': "Member added to shard "+str(shardID)}
            return response, 200

        # Migrate the kvs from the shard into the node
        # First check if were already in this shard...
        if shardID == appdata.shardID:
            response = {'message': "Node already in shard " + str(shardID)}
            return response, 404

        # Need to check if leaving will violate fault-tolerance (less than 2 nodes in the shard)
        nodesInShard = getShardIDMembers(appdata.shardID)
        if len(nodesInShard) < 3:
            response = {'message': "Fault-Tolerance error" +
                        str(appdata.shardID)}
            return response, 401

        appdata.shardID = shardID
        boot()
        response = {'message': "Member added to shard "+str(shardID)}
        return response, 200


class reshard(Resource):
    def put(self):
        data = json.loads(request.data)
        shardCount = data['shard-count']

        # Check if their are enough nodes for each shard to have two nodes
        if len(appdata.runningReplicas) / 2 < shardCount:
            # Fail to reshard due to not enough nodes
            response = {
                "message": "Not enough nodes to provide fault-tolerance with the given shard count!"}
            return response, 400

        shardPayloads = {}
        shardMemberSAs = {}
        inputKVSs = {}
        outputKVSs = {}

        # Get the shardIDs
        shardIDs = getShardIDs()

        # Prep the payloads and recipients for sending
        for shardID in shardIDs:
            shardMemberSAs[shardID] = getShardIDMembers(shardID)[0]
            shardPayloads[shardID] = json.dumps({'SA': appdata.SOCKET_ADDRESS,
                                                 'BOOT': True,
                                                 'shard-id': shardID})

        # Send out the requests, store their kvs
        # split into shard1kvs, shard2ks, etc
        endpoint = '/key-value-store-view'
        for shardID in shardIDs:
            inputKVSs[shardID] = sendRequest(
                "PUT", shardMemberSAs[shardID], endpoint, shardPayloads[shardID]).data['kvs']

        # initialize each new output kvs
        appdata.SHARD_COUNT = shardCount
        for i in range(shardCount):
            outputKVSs[i+1] = {}

        # Print out each kvs
        # Recompute hashes, store in output KVS
        for shardID in shardIDs:
            for key, value in inputKVSs[shardID].items():
                newShardID = findShard(key)
                outputKVSs[newShardID][key] = value

        newShardIDs = {}
        sortedNodes = sorted(appdata.runningReplicas)
        for index, SA in enumerate(sortedNodes):
            newShardIDs[SA] = index % shardCount + 1

        base = "/key-value-store-shard/add-member/"
        for SA in sortedNodes:
            newShardID = newShardIDs[SA]
            endpoint = base + str(newShardID)
            payload = json.dumps({'socket-address': SA,
                                  'kvs': outputKVSs[newShardID],
                                  'shard-count': shardCount})
            sendRequest("PUT", SA, endpoint, payload)
        # determine which SA goes to which shard (based on position)
        # for each SA in runningReplicas
        # sent put request to add-member/shardID endpoint, with kvs attached and SA
        response = {"message": "Resharding done successfully"}
        return response, 200
