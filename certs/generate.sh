#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

openssl genrsa -out ca.key 4096 2>/dev/null
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
    -subj "/CN=httpmark Test CA/O=httpmark/C=US" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"

openssl genrsa -out httpbin.local.key 2048 2>/dev/null
openssl req -new -key httpbin.local.key -out httpbin.local.csr \
    -subj "/CN=httpbin.local/O=httpmark/C=US"
openssl x509 -req -in httpbin.local.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out httpbin.local.crt -days 365 -extfile server.ext 2>/dev/null

cat httpbin.local.crt httpbin.local.key > httpbin.local.pem

echo "certs generated: ca.crt, httpbin.local.{key,crt,pem}"
