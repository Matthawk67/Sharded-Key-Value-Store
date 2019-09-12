#!/bin/sh
curl --request DELETE --header "Content-Type: application/json" \
--write-out "%{http_code}\n" --data '{causal-metadata": "'$2'"}' \
"http://localhost:8082/key-value-store/$1"
