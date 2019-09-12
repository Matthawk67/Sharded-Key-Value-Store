# kvStoreRest.py

import time
import json
import appdata
from flask import Flask, request
from flask_restful import Resource
from invalidUsage import InvalidUsage
from RequestHelper import *


def addVersion(key, data):
    value = data['value'] if 'value' in data else None
    tempTuple = (key, value, data['causal-metadata'])
    appdata.versions[appdata.version] = tempTuple


def updateCausalMD(key, data):
    clientMD = strToList(data["causal-metadata"])
    for version in clientMD:
        intVersion = int(version)
        if intVersion not in appdata.versions:
            requestVersion(intVersion)
        while intVersion not in appdata.versions:
            time.sleep(1)
    # Fortmat the version
    # print(appdata.versions)
    intKeys = [int(x) for x in appdata.versions.keys()]
    appdata.version = (max(intKeys)) if intKeys else 0
    appdata.version = appdata.version + 1
    # Fortmat the CausalMD
    appdata.CausalMD = clientMD
    appdata.CausalMD.append(appdata.version)
    # Copy string version & causalMD to data
    data["version"], data["causal-metadata"] = getDataStrings()
    return json.dumps(data)


def handleVersioning(broadcast, key, data):
    responses = []
    if request.remote_addr not in appdata.trustedIPs:
        updatedData = updateCausalMD(key, data)
        responses = broadcast(key, updatedData)
    elif request.remote_addr not in appdata.SOCKET_ADDRESS:
        appdata.version = int(data["version"])
        appdata.CausalMD = strToList(data['causal-metadata'])
    addVersion(key, data)
    return responses


def handleWrongShard(responses):
    if request.remote_addr in appdata.trustedIPs:
        response = {"message": "Not responsible for key"}
        return response, 406
    for nodeResponse in responses:
        if nodeResponse.result and nodeResponse.status != 406:
            return nodeResponse.data, nodeResponse.status
    response = {"message": "Couldn't find the shard"}
    return response, 406


class KeyValueStore(Resource):
    def put(self, key):
        data = json.loads(request.data)
        value = data['value'] if 'value' in data else None
        lengthError = True if len(key) > 50 else False

        if value is None:
            response = {"error": "Value is missing", "message": "Error in PUT"}
            raise InvalidUsage(response, 400)

        if lengthError:
            response = {"error": "Key is too long",
                        "message": "Error in PUT"}
            raise InvalidUsage(response, 400)

        if request.remote_addr is appdata.SOCKET_ADDRESS:
            response = {"message": "Ignoring Broadcast to Self"}
            return response, 200

        keyShardID = findShard(key)
        wrongShard = True if keyShardID != appdata.shardID else False
        broadcast = putKVSBroadcastBlock if wrongShard else putKVSBroadcast
        responses = handleVersioning(broadcast, key, data)

        if wrongShard:
            return handleWrongShard(responses)

        versionString, causalString = getDataStrings()

        if key not in appdata.kvs:
            appdata.kvs[key] = value
            response = {"message": "Added successfully",
                        "replaced": False,
                        "version": versionString,
                        "causal-metadata": causalString,
                        "shard-id": str(keyShardID)}
            return response, 201
        else:
            appdata.kvs[key] = value
            response = {"message": "Updated successfully",
                        "replaced": True,
                        "version": versionString,
                        "causal-metadata": causalString,
                        "shard-id": str(keyShardID)}
            return response, 200

    def get(self, key):

        keyShardID = findShard(key)

        if keyShardID != appdata.shardID:
            endpoint = "/key-value-store/" + key
            responses = broadcastToShardMembers(
                keyShardID, sendGet, endpoint, None)
            for nodeResponse in responses:
                if nodeResponse.result:
                    return nodeResponse.data, nodeResponse.status

        if key not in appdata.kvs:
            response = {"doesExist": False,
                        "error": "Key does not exist",
                        "message": "Error in GET"}
            raise InvalidUsage(response, 404)

        versionString, causalString = getDataStrings()
        response = {"doesExist": True,
                    "message": "Retrieved successfully",
                    "value": appdata.kvs[key],
                    "version": versionString,
                    "causal-metadata": causalString,
                    "shard-id": str(keyShardID)}
        return response, 200

    def delete(self, key):
        if key not in appdata.kvs:
            response = {"doesExist": False,
                        "error": "Key does not exist",
                        "message": "Error in DELETE"}
            raise InvalidUsage(response, 404)

        data = json.loads(request.data)

        if request.remote_addr is appdata.SOCKET_ADDRESS:
            response = {"Message": "Ignoring Broadcast to Self"}
            return response, 200

        keyShardID = findShard(key)
        broadcast = deleteKVSBroadcast if keyShardID == appdata.shardID else deleteKVSBroadcastBlock
        responses = handleVersioning(broadcast, key, data)

        if keyShardID != appdata.shardID:
            return handleWrongShard(responses)

        versionString, causalString = getDataStrings()

        del appdata.kvs[key]
        response = {"doesExist": True,
                    "message": "Deleted successfully",
                    "version": versionString,
                    "causal-metadata": causalString,
                    "shard-id": str(keyShardID)
                    }
        return response, 200
