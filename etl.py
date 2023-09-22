import boto3
import json
import hashlib
import psycopg2

session = boto3.Session(
    aws_access_key_id='dummy_access_key',
    aws_secret_access_key='dummy_secret_key',
    region_name='us-east-1'
)
# Step 1: Setup SQS client
sqs = boto3.client('sqs',region_name="us-east-1",endpoint_url="http://localhost:4566")

# Step 2: Connect to Postgres
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

def mask_field(value):
    """Mask a given value using a consistent hash."""
    return hashlib.sha256(value.encode()).hexdigest()

while True:
    # Fetch a message from SQS
    messages = sqs.receive_message(QueueUrl="http://localhost:4566/000000000000/login-queue", MaxNumberOfMessages=1)
    
    # Check if there are no more messages
    if 'Messages' not in messages:
        break
    
    # Process the message
    message = messages['Messages'][0]
    body = json.loads(message['Body'])

    # Mask PII data
    body["device_id"] = mask_field(body["device_id"])
    body["ip"] = mask_field(body["ip"])
    
    # Write to Postgres
    insert_query = """INSERT INTO user_logins (user_id, device_type, masked_ip, masked_device_id, locale, app_version)
                      VALUES (%s, %s, %s, %s, %s, %s);"""
    cursor.execute(insert_query, (
        body["user_id"],
        body["device_type"],
        body["ip"],
        body["device_id"],
        body["locale"],
        "000"
        #body["app_version"]
       # body["create_date"]
    ))

    # Delete message from SQS to prevent reprocessing
    sqs.delete_message(QueueUrl="http://localhost:4566/000000000000/login-queue", ReceiptHandle=message['ReceiptHandle'])

# Commit the transaction and close the connection
conn.commit()
cursor.close()
conn.close()