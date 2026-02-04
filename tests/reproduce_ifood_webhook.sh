#!/bin/bash

# Configuration
API_URL="https://ain6spik95.execute-api.us-east-1.amazonaws.com/prod/webhook/ifood"
WEBHOOK_SECRET="test_secret" # This won't work for signature validation unless we update the secret in AWS, 
                             # BUT our current debug mode allows any signature.
                             # For real testing, we rely on the "debug mode" or need the real secret.

echo "=================================================="
echo "iFood Webhook Reproduction Suite"
echo "Target URL: $API_URL"
echo "=================================================="

# Function to send request
send_request() {
    local event_type=$1
    local payload=$2
    local signature=$3

    echo ""
    echo "Testing Event: $event_type"
    echo "Payload: $payload"
    echo "Sending..."

    curl -s -v -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "X-IFood-Signature: $signature" \
        -d "$payload"
    
    echo ""
    echo "--------------------------------------------------"
}

# 1. Connection Test (The one causing issues)
# Based on logs, iFood sends a 'check' or empty payload for connection tests.
# We'll send the 'check' event we saw in logs.
PAYLOAD_CHECK='{"eventId": "test_conn_1", "eventType": "check", "merchantId": "1"}'
send_request "Connection Test (check)" "$PAYLOAD_CHECK" "test_signature_check"

# 2. Order Placed (Realistic Scenario)
PAYLOAD_ORDER='{
    "eventId": "test_order_1",
    "eventType": "order.placed",
    "merchantId": "1",
    "orderId": "order_123",
    "createdAt": "2026-01-30T12:00:00Z",
    "customer": {
        "id": "cust_1",
        "name": "John Doe",
        "phone": "5511999999999"
    },
    "items": [
        {
            "id": "item_1",
            "name": "Pizza",
            "quantity": 1,
            "unitPrice": 50.00,
            "totalPrice": 50.00
        }
    ],
    "total": {
        "subTotal": 50.00,
        "deliveryFee": 5.00,
        "orderAmount": 55.00
    },
    "payments": [
        {
            "method": "CREDIT_CARD",
            "value": 55.00,
            "type": "ONLINE"
        }
    ]
}'
send_request "Order Placed" "$PAYLOAD_ORDER" "test_signature_order"

# 3. Order Cancelled
PAYLOAD_CANCEL='{
    "eventId": "test_cancel_1",
    "eventType": "order.cancelled",
    "merchantId": "1",
    "orderId": "order_123",
    "cancellationReason": "Customer request",
    "cancelledAt": "2026-01-30T12:10:00Z"
}'
send_request "Order Cancelled" "$PAYLOAD_CANCEL" "test_signature_cancel"

echo "Done."
