# Sharded Key Value Store

### Prerequisites

- Python3
- Flask
- Flask Restful
- Docker

### Installing

For running within docker, you only need docker installed.

For running locally, you need Python3 installed, along with the module flask_restful.
After installing Python3 Running `pip install flask_restful` will install flask_restful
and it's dependencies, namely flask.

### Makefile

The Makefile is in the root directory of the repository.

The makefile contains a number of useful commands which are documented below:

Running `make clean` will clean the host of any subnets

Running `make prune` will run the docker pruning utility

Running `make build` will first clean the system of all subnets, create a new subnet, and then build the docker image

Running `make subnet` will create the required subnet for the replicas. This command is not typically needed in practice

Running `make test` will clean the system, and then run the test script provided for the assignment

Running `make node=node<?>` will clean the system of any container with the name specified, build the subnet if it does
not already exist and run the node. It is recommended to build the image if you have not done
so yet. An example of this command is provided below:

  ```
  make node=node1
  * This will make node 1
  
  make node=node2
  ...
  ...
  ...
  
  make node=node6
  ```
The makefile supports creating 6 nodes via this command. A seventh node has macros defined which can be used with command below.

Running `make ungrouped` will create a seventh node which does not belong to a shard at startup. This command can be useful for adding nodes to a shard and testing the put request. 


### Dockerfile

Dockerfile uses a base image of `python:3.7-alpine`, a lightweight image with the
essentials for running a python app. Installs `flask_restful` with pip and continues
to export the server python file as the flask app then running it with host 0.0.0.0
and port 8080.

### Starting the Nodes

The included dockerfile and makefile will do all the heaving lifting as far as getting the servers running:

These commands assume you are using a Linux environment of some form. The exact commands may vary based on your system.

All replicas can be started with the commands from the makefile. You may omit the 'sudo' in the commands below if docker already has super-user privileges.

A typical launch process for starting all six nodes from scratch is as follows:

  ` $ sudo service docker start` - If docker is already started, then you can skip this command  
  ` $ sudo make prune`  
  ` $ sudo make clean`  
  ` $ sudo make build`  
  ` $ sudo make node=node1`   
  ` $ sudo make node=node2`   
  ` $ sudo make node=node3`   
  ` $ sudo make node=node4`   
  ` $ sudo make node=node5`   
  ` $ sudo make node=node6`      

### Usage

There are three main ways to interact with the server once it is running:

##### Get

To retrieve the value of a key in the dictionary, you can type a command such as:

```
$ curl --request GET --header "Content-Type: application/json" --write-out "%{http_code}\n" http://10.10.0.2:8082/key-value-store/course1
```

If the key provided exists, a json object will be returned with the following format and a status code of 200.
```
{"doesExist": True, "message": "Retrieved successfully", "value": <Value> }
```

Otherwise, an object of the following format will be returned with a status code of 404.
```
{"doesExist": False, "error": "Key does not exist", "message": "Error in GET"}
```
##### Put

To place a key-value pair into the dictionary, you can type a command such as:

```
$ curl --request PUT --header "Content-Type: application/json" --write-out "%{http_code}\n" --data '{"value": "Distributed Systems"}' http://10.10.0.2:8082/key-value-store/course1
```

If no key currently exists for a given input, a json object will be returned with the following format and a status code of 201:
```
{"message": "Added successfully", "replaced": False, "version": <Current Version>,
                "causal-metadata": <Metadata>}
```
If a key exists with the same name, you will recieve:
```
{"message": "Updated successfully", "replaced": True, "version": <Current Version>,
                "causal-metadata": <Metadata> }
```

Other error checking exists for the situation in which a key is empty or too long. You will recieve a json object with a status code of 400 to the effect of:
```
{error, message}
```

##### Delete
To remove a key-value-pair from the dictionary, you can type a command such as:

```
$ curl --request DELETE --header "Content-Type: application/json" --write-out "%{http_code}\n" http://10.10.0.2:8082/key-value-store/course1
```

This command has two possible returns. If the key existed and was deleted succesfully, you will recieve the following json object with a status code of 200:

```
{"doesExist": True, "message": "Deleted successfully"}
```

Otherwise, you will recieve this object with a status code of 404:

```
{"doesExist": False, "error": "Key does not exist", "message": "Error in DELETE"}
```

## Directories

- [src](src/) (Contains souce code)
- [scripts](scripts/) (Contains a few useful scripts which execute certain long requests)
- [documents](documents/) (Contains additional files for like contribution, mechanism descriptions, ect.)

## [kvStoreRest.py](src/kvStoreRest.py)

Refer closely to documentation on [Flask][flasklink] and [Flask Restful][restfullink].

##### Returns & Exceptions

Responses are json objects. The assignments so far require a json response followed
by the error code. Example of instantiating a response:

```python
response = {"foo": True,
            "bar": "test",
            "baz": self.data[key]}
```

For a valid request / usage we would return like:

```python
return response, 200
```

For an invalid usage, we raise an exception using the InvalidUsage class imported from
[invalidUsage.py](src/invalidUsage.py), and detail the status error code like so:

```python
response = {"error":"Invalid Usage",
            "foo": 2,
            "bar": data}

raise InvalidUsage(response, status_code=404)
```

We can also use the InvalidUsage class for debugging. Response can be either a dictionary
or a string, (or anything for that matter), but traditionally a string or dictionary. Passing
a dictionary will parse the dictionary into a json object. Passing a string will simply
return that string instead of a json object.

```python
response="Hello World"

raise InvalidUsage(response, status_code=404)
```

will return:

```
Hello World
404
```

## [appdata.py](src/appdata.py)

This file contains all the internal state information for each running replica. This data includes things like its key-value-store, its versioning data, the socket addresses of its peers, etc. More information about what exactly is stored in the internal state can be found in the file itself. This file contains no functions beyond an init. 


## [main.py](src/main.py)

This file contains all the code needed to start the flask server. This includes tasks like parsing the arguments given to the container, initially broadcasting to other peers on starup to see if the network is already running, pinging other servers, error handling, and is the main entry point for program execution. 

##### App exception handler

According to this [post][handlerpost]`flask_restful` doesn't use custom error handlers. Although flask
supports custom error handlers, `flask_restful` overrides the handlers from flask after
instantiating the `api` object. This previously resulted in varying behavior based on when
the flask debug flag was set. To overcome this:

```python
app = Flask(__name__)
handle_exception = app.handle_exception
handle_user_exception = app.handle_user_exception
api = Api(app)
app.handle_exception = handle_exception
app.handle_user_exception = handle_user_exception

api.add_resource(KeyValueStore, "/key-value-store/<string:key>")
api.add_resource(kvsView, "/key-value-store-view")
```

This code copies the exception handlers from the flask app, then restores the handlers after
instantiating the `api` object. This means **only the `flask` exception handlers are available**
to this project and the **`flask_restful` exception handlers are not.**

## [invalidUsage.py](src/invalidUsage.py)

This file contains one class and aids in performing checking on inputs. 

## [kvsView.py](src/kvsView.py)

This file contains all of the functions to the control the communcation between replicas. 

## [RequestHelper.py](src/RequestHelper.py)

This file contains a variety of utility functions used for broadcasting and communcating between replicas. It also contains code for handling concurrent requests and broadcasts using multiprocessing. 

Asyncronous Broadcasts are achieved by using Pythons multiprocessing library. The function that executes this is described below:

```
# Asynchronous Broadcast method
def broadcast(func, endpoint, data):
    threadPool = Pool(processes=len(appdata.runningReplicas))
    threadParams = []
    for SA in appdata.runningReplicas:
        params = {}
        params['SA'] = SA
        params['endpoint'] = endpoint
        params['data'] = data
        threadParams.append(params)
    results = threadPool.map(func, threadParams)
    threadPool.close()
    return results
```

This function starts a threadpool and assigns an argument list for each thread it will spawn. These threads take a specific socket address and the required endpoint and data and are individually tasked with communicating with the replica in their parameters. 

```
# Generic Template for sending a DELETE or PUT Request
def sendRequest(type, SA, endpoint, data):
    route = "http://" + SA + endpoint
    try:
        if type == "DELETE":
            _ = requests.delete(route, data=data, timeout=5)
        elif type == "PUT":
            _ = requests.put(route, data=data, timeout=5)
    except(requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        print("Failed to connect, replica is down")
        return False, SA
    return True, SA
```

Each thread takes a generalzied sendRequest method, which specifys whether it is sending a put or delete request to the replica. This method also tracks whether the replica in question responds. If it does not, it broadcasts to all other active replicas to remove the unresponsive replica from their view. This allows the system to quickly track which replicas are down and to ajust their broadcasts accordingly. When the replica comes back online, it will broadcast to all of its peers that it is ready to begin recieving requests again. 

## [kvsShard.py](src/kvsShard.py)

This file contains the code to handle shards and their various operations. These responses are defined as the classes below:

```
# This class handles the get requests sent to retreve the shard ID of a node
class nodeShardID(Resource):

# This class handles get requests sent to get all active shard ID's
class kvsShardIDs(Resource):

# This class handles the get requests to get all current members of a specified shard ID
class shardIDMembers(Resource):

# This class handles the get requests to get the number of keys contained within a shard
class shardIDKeyCount(Resource):

# This class handles put requests to add an ungrouped node to a specified shard
class addMember(Resource):

# This class handle the special reshard put request which reshards the distribution of nodes 
into groups of atleast two for a specified number of shards. Hence three shards will require 
six nodes at a minimum
class reshard(Resource):
```
