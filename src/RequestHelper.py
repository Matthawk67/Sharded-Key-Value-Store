# kvStoreRest.py

import requests
import appdata
import json
import time
from hashlib import md5

from multiprocessing import Pool, Process
from threading import Thread

# class of text colors for cleaner console output


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    VIEW = '\033[34m'
    BOOT = '\033[33m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class nodeResponse:
    def __init__(self, result, SA, data, status):
        self.result = result
        self.SA = SA
        self.data = data
        self.status = status


# Hash a key to find its shard
def findShard(key):
    hashedKey = md5(key.encode('utf8')).digest()[0]
    shardID = hashedKey % appdata.SHARD_COUNT + 1
    return shardID


# Print the view
def printView(msg=""):
    print("\n" + bcolors.BOOT + msg + bcolors.ENDC + bcolors.VIEW + " VIEW: " + bcolors.ENDC,
          sorted(appdata.runningReplicas), "\n", flush=True)


# turn a string into a list
def strToList(s):
    newList = s.split(",")
    intList = []
    if not s:
        return intList
    for version in newList:
        intList.append(int(version))
    return intList


# Turn a list into a string
def listToString():
    strings = [str(version) for version in sorted(appdata.CausalMD)]
    return ",".join(strings)


# prep data for outgoing responses
def getDataStrings():
    return str(appdata.version), listToString()


# Generic Template for sending a DELETE or PUT Request
def sendRequest(type, SA, endpoint, data):
    route = "http://" + SA + endpoint
    try:
        if type == "DELETE":
            req = requests.delete(route, data=data, timeout=3)
        elif type == "PUT":
            req = requests.put(route, data=data, timeout=3)
        elif type == "GET":
            req = requests.get(route, timeout=3)
    except(requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # print("Failed to connect, replica is down")
        return nodeResponse(False, SA, {}, 408)
    return nodeResponse(True, SA, req.json(), req.status_code)


# Function Wrapper to send Put requests
def sendPut(params):
    return sendRequest("PUT", params['SA'], params['endpoint'], params['data'])


# Function Wrapper to send DELETE requests
def sendDelete(params):
    return sendRequest("DELETE", params['SA'], params['endpoint'], params['data'])


# Function Wrapper to send GET requests
def sendGet(params):
    return sendRequest("GET", params['SA'], params['endpoint'], params['data'])


# Async broadcast for generic group of SA's, nonblocking
def broadcastToGroup(group, func, endpoint, data):
    if len(group) == 0:
        print("Error: trying to broadcast to empty group", flush=True)
        return []
    threadPool = Pool(processes=len(group))
    threadParams = []
    for SA in group:
        if SA == appdata.SOCKET_ADDRESS:
            continue
        params = {}
        params['SA'] = SA
        params['endpoint'] = endpoint
        params['data'] = data
        threadParams.append(params)
    responses = threadPool.map(func, threadParams)
    threadPool.close()
    return responses

# Asynchronous Broadcast method iterating over runningReplicas


def broadcast(func, endpoint, data):
    group = appdata.runningReplicas
    return broadcastToGroup(group, func, endpoint, data)


# Asynchronous Broadcast method iteration over shardID members
def broadcastToShardMembers(shardID, func, endpoint, data):
    group = getShardIDMembers(shardID)
    return broadcastToGroup(group, func, endpoint, data)


# Function Wrapper to broadcast, then broadcast a delete for each
# unresponsive replica
def broadcastThenDelete(func, endpoint, data):
    removalSet = set()
    responses = broadcast(func, endpoint, data)
    for nodeResponse in responses:
        if not nodeResponse.result:
            removalSet.add(nodeResponse.SA)

    appdata.runningReplicas = appdata.runningReplicas - removalSet

    for SA in removalSet:
        deleteReplicaBroadcast(SA)

    return responses


# Helper function to generalize KVS broadcast, nonblocking
def genericKVSBroadcast(func, key, data):
    endpoint = "/key-value-store/" + key
    thread = Thread(target=broadcastThenDelete, args=(func, endpoint, data))
    thread.start()


# Function Wrapper to Perform KVS Put Broadcast, nonblocking
def putKVSBroadcast(key, data):
    genericKVSBroadcast(sendPut, key, data)


# Function Wrapper to Perform KVS Delete Broadcast, nonblocking
def deleteKVSBroadcast(key, data):
    genericKVSBroadcast(sendDelete, key, data)


# Helper function to generalize KVS broadcast, blocking
def genericKVSBroadcastBlock(func, key, data):
    endpoint = "/key-value-store/" + key
    responses = broadcastThenDelete(func, endpoint, data)
    return responses


# Function Wrapper to Perform KVS Put Broadcast, blocking
def putKVSBroadcastBlock(key, data):
    return genericKVSBroadcastBlock(sendPut, key, data)


# Function Wrapper to Perform KVS Delete Broadcast, blocking
def deleteKVSBroadcastBlock(key, data):
    return genericKVSBroadcastBlock(sendDelete, key, data)


# Function Wrapper to Perform VIEW Delete Broadcast
def deleteReplicaBroadcast(SA):
    data = json.dumps({'SA': SA})
    endpoint = '/key-value-store-view'
    thread = Thread(target=broadcast, args=(sendDelete, endpoint, data))
    thread.start()


# broadcast to all nodes, return all nodes with shardID
def getShardIDMembers(shardID):
    endpoint = "/key-value-store-shard/node-shard-id"
    responses = broadcastThenDelete(sendGet, endpoint, {})
    members = set()
    if shardID == appdata.shardID:
        members.add(appdata.SOCKET_ADDRESS)
    for nodeResponse in responses:
        if nodeResponse.result and nodeResponse.data['shard-id'] == str(shardID):
            members.add(nodeResponse.SA)
    return sorted(members)


def getShardIDs():
    endpoint = "/key-value-store-shard/node-shard-id"
    responses = broadcastThenDelete(sendGet, endpoint, {})
    shardIDs = set()
    if appdata.shardID != 'None':
        shardIDs.add(appdata.shardID)
    for nodeResponse in responses:
        if nodeResponse.result and nodeResponse.data['shard-id'] != 'None':
            shardIDs.add(int(nodeResponse.data['shard-id']))
    return shardIDs


# broadcast to all shardID nodes, return key count of shardID
def getShardIDKeyCount(shardID):
    if shardID == appdata.shardID:
        return len(set(appdata.kvs.keys()))
    endpoint = "/key-value-store-shard/shard-id-key-count/" + str(shardID)
    responses = broadcastToShardMembers(shardID, sendGet, endpoint, {})
    for nodeResponse in responses:
        if nodeResponse.result:
            return nodeResponse.data['shard-id-key-count']
    return 0


# Boot sequence
def boot():
    def helper():
        time.sleep(1)
        # Print the initial view
        printView("PRE-BOOT")
        # data we are sending
        data = json.dumps({'SA': appdata.SOCKET_ADDRESS,
                           'BOOT': True,
                           'shard-id': appdata.shardID})
        # endpoint we are sending to
        endpoint = '/key-value-store-view'
        # Send to all replicas, then delete any unresponsive ones
        responses = broadcastThenDelete(sendPut, endpoint, data)
        # Print the view after broadcasting
        printView("POST-BOOT")

        for nodeResponse in responses:
            if nodeResponse.result:
                data = nodeResponse.data
                # Chck if kvs exists and one sent is not empty
                kvsExists = True if 'kvs' in data and data['kvs'] else False
                # Chck if kvs exists and one sent is not empty
                versionsExists = True if 'versions' in data and data['versions'] else False
                # Get the shard ID from data
                shardID = data['shard-id'] if 'shard-id' in data else None
                # Set the kvs if it exists & non empty
                appdata.kvs = data['kvs'] if kvsExists else appdata.kvs
                # Set the versions dictionary if it exists & non empty
                appdata.versions = data['versions'] if versionsExists else appdata.versions
                # Add the shardID to our shardIDs list
                if shardID != 'None':
                    appdata.shardIDs.add(shardID)
            else:
                print("Failed to connect to " + nodeResponse.SA +
                      " replica is down", flush=True)

    thread = Thread(target=helper)
    thread.setDaemon(True)
    thread.start()


# Request a version, delete / store key-value pair it in kvs
def requestVersion(version):
    data = json.dumps({'SA': appdata.SOCKET_ADDRESS,
                       'version': version})
    endpoint = '/key-value-store-view'
    responses = broadcastThenDelete(sendPut, endpoint, data)
    for nodeResponse in responses:
        data = nodeResponse.data
        if 'version' not in data:
            continue
        VERSION = data['version']
        appdata.versions[int(version)] = VERSION
        key, value, _ = VERSION
        if value is None:
            del appdata.kvs[key]
        else:
            appdata.kvs[key] = value
