import json
import boto3
import os
from multiprocessing import Process
from io import BytesIO

eventSqsUrl = os.environ.get('eventSqsUrl')
invocationSqsUrl = os.environ.get('invokationSqsUrl')

def lambda_handler(event, context):
    print(event)

    cnt = 0    

    sqs_client = boto3.client('sqs')

    # push to SQS
    try:
        resp = sqs_client.receive_message(
            QueueUrl=eventSqsUrl, 
            MaxNumberOfMessages=10,
            VisibilityTimeout=30
        )

        print('resp: ', resp)

    except Exception as e:        
        print('Fail to delete the queue message: ', e)
        


        
    #    body = {
    #        'eventId': eventId,
    #        'eventTimestamp': eventTimestamp,
    #        'bucketName': bucketName,
    #        'key': key
    #    }
    #    print('body: ', body)

        # push to SQS
    #    try:
    #        sqs_client.send_message(
    #            QueueUrl=sqsUrl, 
    #            MessageAttributes={},
    #            MessageDeduplicationId=eventId,
    #            MessageGroupId="putEvent",
    #            MessageBody=json.dumps(body)
    #        )

    #   except Exception as e:        
    #        print('Fail to delete the queue message: ', e)
        
    
    return {
        'statusCode': 200,
    }        