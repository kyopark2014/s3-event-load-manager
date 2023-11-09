import json
import boto3
import os
import datetime
import uuid

sqs_client = boto3.client('sqs')
sqsUrl = os.environ.get('queueS3event')

def lambda_handler(event, context):
    # print(event)

    s3eventInfo = []
    for record in event['Records']:
        print("record: ", record)

        s3 = record['s3']
        bucketName = s3['bucket']['name']
        key = s3['object']['key']

        print('bucketName: '+bucketName+', key: '+key)

        eventId = str(uuid.uuid1())
        print('eventId: ', eventId)

        d = datetime.datetime.now()
        # timestamp = str(d)[0:19]  # min
        timestamp = str(d)
        body = json.dumps({
            'bucket_name': bucketName,
            'key': key
        }) 
        
        s3EventInfo = {
            'event_id': eventId,
            'event_timestamp': timestamp,
            'event_body': body
        }
        
        # push to SQS
        try:
            sqs_client.send_message(
                QueueUrl=sqsUrl, 
                MessageAttributes={},
                MessageDeduplicationId=eventId,
                MessageGroupId="putEvent",
                MessageBody=json.dumps(s3EventInfo)
            )

        except Exception as e:        
            print('Fail to delete the queue message: ', e)
        
        s3eventInfo.append({
            'bucketName': bucketName,
            'key': key
        })
        
    return {
        'statusCode': 200,
        'result': json.dumps(s3eventInfo),
    }