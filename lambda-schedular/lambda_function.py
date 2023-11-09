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

    cnt = 0    

    print('QueueUrl: ', eventSqsUrl)
    
    # get message from S3 event SQS
    try:
        sess = boto3.session.Session()
        sqs = sess.resource("sqs")
        queue = sqs.get_queue_by_name(QueueName='queue-s3-putEvent.fifo')
        print('queue: ', queue)

        messages = queue.receive_messages()
        print('Amount of existing Queue messages',len(messages))
        for message in messages:
            print('msg:',message.body)
            message.delete()
        #time.sleep(5)
        
        
        
        url_fifo = eventSqsUrl
        msg_list = sqs_client.receive_message(QueueUrl=url_fifo, MaxNumberOfMessages=1)
        print('msg_list: ', msg_list)
        
        sqsReceiveResponse = sqs_client.receive_message(
            QueueUrl=eventSqsUrl,
            #message_attribute_names="All", # Receive all custom attributes.
            #MessageAttributeNames=['All'],
            #wait_time_seconds=0, # Do not wait to check for the message.
            #VisibilityTimeout=0,
            #message_attribute_names = ["MessageAttributeName"],
            #MaxNumberOfMessages=10,
            #WaitTimeSeconds=3,
            AttributeNames = ['All'],
            MaxNumberOfMessages=1,
            #VisibilityTimeout=120,
            #receive_request_attempt_id="event",
        )
        print('sqsReceiveResponse: ', sqsReceiveResponse)
        
        print(f"Number of messages received: {len(sqsReceiveResponse.get('Messages', []))}")
        
        for message in sqsReceiveResponse.get("Messages", []):
            message_body = message["Body"]
            print(f"Message body: {json.loads(message_body)}")
            print(f"Receipt Handle: {message['ReceiptHandle']}")
        
        

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