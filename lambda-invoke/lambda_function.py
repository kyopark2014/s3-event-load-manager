import json
import boto3
import os

s3 = boto3.client('s3')
sqs = boto3.client('sqs')
sqsUrl = os.environ.get('invokationSqsUrl')

def lambda_handler(event, context):
    #print(event)
    #print(f'event: {json.dumps(event)}')

    for record in event['Records']:
        print("record: ", record)

        receiptHandle = record['receiptHandle']
        print("receiptHandle: ", receiptHandle)

        body = record['body']
        print("body: ", body)

        jsonbody = json.loads(body)
        
        eventId = jsonbody['event_id']
        print("eventId: ", eventId)

        eventTimestamp = jsonbody['event_timestamp']
        print("eventTimestamp: ", eventTimestamp)

        messageBody = json.loads(jsonbody['event_body'])
        bucketName = messageBody['bucketName']
        print("bucketName: ", bucketName)

        key = messageBody['key']
        print("key: ", key)

        # delete queue
        try:
            sqs.delete_message(QueueUrl=sqsUrl, ReceiptHandle=receiptHandle)
        except Exception as e:        
            print('Fail to delete the queue message: ', e)
                
    statusCode = 200
    return {
        'statusCode': statusCode,
    }