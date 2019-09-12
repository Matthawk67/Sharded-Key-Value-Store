# kvsView file

from functools import wraps
from flask import Flask, request
from flask_restful import Resource
from invalidUsage import InvalidUsage
import json
import appdata
from RequestHelper import deleteReplicaBroadcast, getDataStrings, printView


# Method Decorator to Check if a request is from a Trusted IP
def isReplica(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.remote_addr not in appdata.trustedIPs:
            response = {"error": "not a replica",
                        "message": "Error in KVSVIEW"}
            raise InvalidUsage(response, 401)
        else:
            return func(*args, **kwargs)
    return wrapper

# App resource. Handles different requests and forwards request to
# main node.


def addToView(SA):
    if SA not in appdata.runningReplicas:
        appdata.runningReplicas.add(SA)
        printView()


def removeFromView(SA):
    if SA in appdata.runningReplicas:
        appdata.runningReplicas.remove(SA)
        printView()


class kvsView(Resource):
    # method_decorators = [isReplica]

    def put(self):
        # Get the data from the request
        data = json.loads(request.data)

        # DATA
        respondToBoot = data['BOOT'] if 'BOOT' in data else False
        VERSION = data['version'] if 'version' in data else False
        SA = data['SA'] if 'SA' in data else None
        # Check if socket Addr was sent
        if SA is None:
            response = {"error": "Socket address wasn't sent",
                        "message": "Error in PUT"}
            raise InvalidUsage(response, 404)

        # Check if we need to send back our KVS
        if respondToBoot:
            addToView(SA)
            shardID = data['shard-id']
            # Add the shardID incase a late node is here
            if shardID != 'None':
                appdata.shardIDs.add(shardID)
            # Only send kvs and versions if they have our shardID
            if shardID != appdata.shardID:
                response = {"Message": "Added node to view",
                            "shard-id": appdata.shardID}
                return response, 200
            else:
                response = {"Message": "Node has same shardID, sending KVS and Versions",
                            "kvs": appdata.kvs,
                            "versions": appdata.versions,
                            "shard-id": appdata.shardID
                            }
                return response, 201

        # check if we need to give another replica a version
        if VERSION:
            addToView(SA)
            if VERSION not in appdata.versions:
                response = {"message": "I dont have it"}
                return response, 404
            else:
                response = {"message": "Here ya go",
                            "version": appdata.versions[VERSION]}
                return response, 201

        # Check if we've already added the Socket Addr to our View
        if SA in appdata.runningReplicas:
            response = {"error": "Socket address already exists in the view",
                        "message": "Error in PUT"}
            raise InvalidUsage(response, 404)

        # Add Socket Addr to our view, Print it
        addToView(SA)

        # Send back a message saying we've added it
        response = {"message": "Replica added successfully to the view"}
        return response, 201

    # This method returns the current status of the running replicas
    def get(self):
        # Format a String To Respond With

        viewString = ''.join(
            str(e) + ',' for e in sorted(appdata.runningReplicas))
        viewString = viewString[:-1]

        # Send Back our response with the formatted View
        response = {"message": "View retrieved successfully",
                    "view": viewString}
        return response, 200

    # This method deletes a replica from the list of running replicas
    def delete(self):
        data = json.loads(request.data)

        # DATA
        SA = data['SA'] if 'SA' in data else None

        # Check if socket Addr was sent
        if SA is None:
            response = {"error": "Socket address wasn't sent",
                        "message": "Error in DELETE"}
            raise InvalidUsage(response, 404)

        # Check if Socket Addr sent is in our View
        if SA not in appdata.runningReplicas:
            response = {"error": "Socket address does not exist in the view",
                        "message": "Error in DELETE"}
            raise InvalidUsage(response, 404)

        # Delete The Replica from our View
        removeFromView(SA)

        # Broadcast Delete to other Replicas
        deleteReplicaBroadcast(SA)

        # Send back our response saying we've deleted the replica
        response = {"message": "Replica deleted successfully from the view"}
        return response, 200
