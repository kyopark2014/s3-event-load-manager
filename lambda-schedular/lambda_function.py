import json
import boto3
import os

eventSqsUrl = os.environ.get('eventSqsUrl')
invocationSqsUrl = os.environ.get('invokationSqsUrl')
sqs_client = boto3.client('sqs')
capacity = 50

def lambda_handler(event, context):
    # print(event)

    # get message from SQS(S3-event)
    cnt = 0
    while True:
        if cnt > capacity:
            break

        try:               
            sqsReceiveResponse = sqs_client.receive_message(
                QueueUrl=eventSqsUrl,
                MaxNumberOfMessages=10,
            )
            print('sqsReceiveResponse: ', sqsReceiveResponse)   
            
            number_of_message = len(sqsReceiveResponse.get('Messages', []))
            print(f"Number of messages received: {number_of_message}")

            if number_of_message==0:
                break
            
            for message in sqsReceiveResponse.get("Messages", []):
                if cnt > capacity:
                    break

                message_body = message["Body"]
                receiptHandle = message['ReceiptHandle']
                print(f"Message body: ", json.loads(message_body))
                print(f"Receipt Handle: ", receiptHandle)

                jsonbody = json.loads(message_body)
                print("event_id: ", jsonbody['event_id'])

                # push to SQS (invokation)
                try:
                    sqs_client.send_message(
                        QueueUrl=invocationSqsUrl, 
                        MessageAttributes={},
                        MessageDeduplicationId=jsonbody['event_id'],
                        MessageGroupId="invokation",
                        MessageBody=message_body
                    )
                    cnt = cnt+1
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
    
    print('used messages: ', cnt+1)

    return {
        'statusCode': 200,
    }        