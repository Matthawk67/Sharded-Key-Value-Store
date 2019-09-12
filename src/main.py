# Misc Python Modules
import os

# Source Modules
import appdata
from kvsView import kvsView
from kvsShard import nodeShardID, kvsShardIDs, shardIDMembers, shardIDKeyCount, addMember, reshard
from kvStoreRest import KeyValueStore
from RequestHelper import boot
from invalidUsage import InvalidUsage

# Flask stuff
from flask import Flask
from flask_restful import Api


# Initialize Flask app.
appdata.init()
app = Flask(__name__)
handle_exception = app.handle_exception
handle_user_exception = app.handle_user_exception
api = Api(app)
app.handle_exception = handle_exception
app.handle_user_exception = handle_user_exception

# View Resources
api.add_resource(kvsView, "/key-value-store-view")

# Shard Node ID resources
api.add_resource(nodeShardID, "/key-value-store-shard/node-shard-id")
api.add_resource(kvsShardIDs, "/key-value-store-shard/shard-ids")

# Shard member resources
api.add_resource(
    shardIDMembers, "/key-value-store-shard/shard-id-members/<int:shardID>")
api.add_resource(
    shardIDKeyCount, "/key-value-store-shard/shard-id-key-count/<int:shardID>")
api.add_resource(
    addMember, "/key-value-store-shard/add-member/<int:shardID>")
api.add_resource(
    reshard, "/key-value-store-shard/reshard")

# Kvs resource
api.add_resource(KeyValueStore, "/key-value-store/<string:key>")

# Error Handling response for generic Invalid Usage
@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    return error.response, error.status_code


# Error handling response for generic 405 error
@app.errorhandler(405)
def method_not_allowed(error):
    return "This method is unsupported.", 405


# Error handling response for generic 404 error
@app.errorhandler(404)
def invalid_endpoint(error):
    return "Visit the /key-value-store/{key_query} endpoint to query the key store table", 404


boot()

if __name__ == '__main__':
    app.run(host=appdata.HOST, port=appdata.PORT)
