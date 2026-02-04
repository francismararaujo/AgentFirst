#!/bin/bash

# Test iFood Connection Test payload
# Based on iFood documentation for webhook connection validation

API_URL="https://ain6spik95.execute-api.us-east-1.amazonaws.com/prod/webhook/ifood"

echo "Testing iFood Connection Test Event"
echo "===================================="

# According to iFood docs, connection test sends an empty POST or minimal payload
# Let's test both scenarios

echo ""
echo "Test 1: Empty body (most likely)"
curl -v -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-IFood-Signature: sha256=test" \
  -d ''

echo ""
echo "===================================="
echo "Test 2: Minimal JSON body"
curl -v -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-IFood-Signature: sha256=test" \
  -d '{}'

echo ""
echo "===================================="
echo "Test 3: With eventType=CONNECTION_TEST"
curl -v -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-IFood-Signature: sha256=test" \
  -d '{"eventType": "CONNECTION_TEST"}'

echo ""
echo "Done."
