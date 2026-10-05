#!/bin/bash

# Configuration
URL="http://localhost:7777/api/supplier/price"
TOKEN="1234"

echo "=== Test 1: Valid Webhook Request ==="
curl -X POST $URL \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"sku": "PROD-00001", "price": 800.00}'
echo -e "\n"

echo "=== Test 2: Invalid Token Request ==="
curl -X POST $URL \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer INVALID_TOKEN" \
     -d '{"sku": "PROD-00001", "price": 579.00}'
echo -e "\n"

echo "=== Test 3: Unknown SKU Request ==="
curl -X POST $URL \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"sku": "UNKNOWN-SKU", "price": 579.00}'
echo -e "\n"
