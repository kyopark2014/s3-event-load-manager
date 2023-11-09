import json
import boto3
import os
from multiprocessing import Process
from io import BytesIO

eventSqsUrl = os.environ.get('eventSqsUrl')
invocationSqsUrl = os.environ.get('invokationSqsUrl')
sqs_client = boto3.client('sqs')
def lambda_handler(event, context):
    print(event)

    print('QueueUrl: ', eventSqsUrl)
    
    # get message from S3 event SQS
    try:       
        sqsReceiveResponse = sqs_client.receive_message(
            QueueUrl=eventSqsUrl,
            MaxNumberOfMessages=1,
        )
        print('sqsReceiveResponse: ', sqsReceiveResponse)        
        print(f"Number of messages received: {len(sqsReceiveResponse.get('Messages', []))}")
        
        for message in sqsReceiveResponse.get("Messages", []):
            message_body = message["Body"]
            receiptHandle = message['ReceiptHandle']
            print(f"Message body: ", json.loads(message_body))
            print(f"Receipt Handle: ", receiptHandle)

            jsonbody = json.loads(message_body)
            print("event_id: ", jsonbody['event_id'])
            # push to SQS
            try:
                sqs_client.send_message(
                    QueueUrl=invocationSqsUrl, 
                    MessageAttributes={},
                    MessageDeduplicationId=jsonbody['event_id'],
                    MessageGroupId="putEvent",
                    MessageBody=message_body
                )
            except Exception as e:        
                print('Fail to push the queue message: ', e)

            print('pushed message: ', jsonbody['event_id'])

            # delete queue
            try:
                sqs_client.delete_message(
                    QueueUrl=eventSqsUrl, 
                    ReceiptHandle=receiptHandle
                )
            except Exception as e:        
                print('Fail to delete the queue message: ', e)

            print('deleted message: ', jsonbody['event_id'])

    except Exception as e:        
        print('Fail to read the queue message: ', e)
            
    return {
        'statusCode': 200,
    }        