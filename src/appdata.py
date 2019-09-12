import os


def destructure(d, *keys):
    return [d[k] if k in d else None for k in keys]


def init():
    global HOST, PORT, SOCKET_ADDRESS, runningReplicas, \
        trustedIPs, kvs, CausalMD, version, \
        versions, SHARD_COUNT, shardID, shardIDs

    VIEW = ""
    SHARD_COUNT = 0
    [HOST, PORT, VIEW, SOCKET_ADDRESS, SHARD_COUNT] = destructure(
        os.environ, 'HOST', 'PORT', 'VIEW', 'SOCKET_ADDRESS', 'SHARD_COUNT')

    runningReplicas = set(VIEW.split(','))
    trustedIPs = set(IP.replace(':8080', '') for IP in runningReplicas)

    if SHARD_COUNT is None:
        shardID = 'None'
        shardIDs = set()
    else:
        SHARD_COUNT = int(SHARD_COUNT)
        shardID = sorted(list(runningReplicas)).index(
            SOCKET_ADDRESS) % SHARD_COUNT + 1
        shardIDs = {shardID}

    kvs = {}
    versions = {}

    CausalMD = []
    version = int(0)
