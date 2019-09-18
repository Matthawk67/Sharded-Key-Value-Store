SOURCE=./Sharded-Key-Value-Store/src/
IMGTAG=Sharded-Key-Value-Store-image
DOCKERSILENCE=&> /dev/null || true
VOLUMEBIND=`pwd`:/Sharded-Key-Value-Store

NET=mynet

SHARD_COUNT=2

node1_IP=10.10.0.2
node2_IP=10.10.0.3
node3_IP=10.10.0.4
node4_IP=10.10.0.5
node5_IP=10.10.0.6
node6_IP=10.10.0.7
node7_IP=10.10.0.8

BINDPORT=8080
node1_PORT=8082
node2_PORT=8083
node3_PORT=8084
node4_PORT=8085
node5_PORT=8086
node6_PORT=8087
node7_PORT=8088

node1_SA=$(node1_IP):$(BINDPORT)
node2_SA=$(node2_IP):$(BINDPORT)
node3_SA=$(node3_IP):$(BINDPORT)
node4_SA=$(node4_IP):$(BINDPORT)
node5_SA=$(node5_IP):$(BINDPORT)
node6_SA=$(node6_IP):$(BINDPORT)
node7_SA=$(node7_IP):$(BINDPORT)


ALL_SA=$(node1_SA),$(node2_SA),$(node3_SA),$(node4_SA),$(node5_SA),$(node6_SA)

node=node1


$(node): clean$(node)
	docker run -v $(VOLUMEBIND) -p $($(node)_PORT):$(BINDPORT) --net=$(NET) --ip=$($(ID)_IP) \
	--name="$(node)" -e SOCKET_ADDRESS="$($(node)_SA)" \
	-e VIEW="$(ALL_SA)" -e SHARD_COUNT=$(SHARD_COUNT) $(IMGTAG)

ungrouped:
	docker run -v $(VOLUMEBIND) -p $(node7_PORT):$(BINDPORT) --net=$(NET) --ip=$(node7_IP) \
	--name="node7" -e SOCKET_ADDRESS="$(node7_SA)" \
	-e VIEW="$(ALL_SA),$(node7_SA)" $(IMGTAG)			

clean$(node):
	@-docker stop $(node) $(DOCKERSILENCE)
	@-docker rm $(node) $(DOCKERSILENCE)

clean:
	@echo "Stopping all containers"
	@-docker stop $(shell docker ps -aq) $(DOCKERSILENCE)
	@echo "Removing all containers" 
	@-docker rm $(shell docker ps -aq) $(DOCKERSILENCE)
	@echo "Removing all subnets" 
	@-docker network rm $(shell docker network ls -q) $(DOCKERSILENCE)

subnet: 
	@echo "Making mynet"
	@-docker network create --subnet=10.10.0.0/16 $(NET) $(DOCKERSILENCE)

build: clean subnet	
	@echo "Building image"
	@-docker build -t $(IMGTAG):latest . $(DOCKERSILENCE)

prune: clean
	@echo "Pruning system"
	@-echo 'y' | docker system prune $(DOCKERSILENCE)
