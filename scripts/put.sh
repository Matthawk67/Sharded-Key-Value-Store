#!/bin/sh
curl --request PUT --header "Content-Type: application/json" \
--write-out "%{http_code}\n" --data '{"value": "'$3'", "causal-metadata": "'$4'"}' \
"http://localhost:$1/key-value-store/$2"
