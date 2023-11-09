import json
import boto3
import os
from multiprocessing import Process
from io import BytesIO
import traceback

tableName = os.environ.get('tableName')
indexName = os.environ.get('indexName')

dynamodb_client = boto3.client('dynamodb')
sqs_client = boto3.client('sqs')
sqsUrl = os.environ.get('sqsUrl')

def lambda_handler(event, context):
    # print(event)

    try:
        response = dynamodb_client.query(
            TableName=tableName,
            IndexName=indexName,
            KeyConditionExpression='event_status = :event_status',
            ExpressionAttributeValues={
                ':event_status': {'S': 'created'}
            }
        )
    except Exception:
            err_msg = traceback.format_exc()
            print('err_msg: ', err_msg)
            raise Exception ("Not able to query from dynamodb")    

    cnt = 0    
    for item in response['Items']:
        if cnt > 10: 
             break
        else: 
            cnt = cnt+1
        
        print('item: ', item)

        eventId = item['event_id']['S']
        eventTimestamp = item['event_timestamp']['S']
        eventStatus = item['event_status']['S']
        print('eventId: '+eventId+', eventTimestamp: '+eventTimestamp+' , status: '+eventStatus)

        eventBody = json.loads(item['event_body']['S'])
        bucketName = eventBody['bucket_name']['S']
        key = eventBody['key']['S']
        print('bucketName: '+bucketName+', key: '+key)
        
        body = {
            'eventId': eventId,
            'eventTimestamp': eventTimestamp,
            'bucketName': bucketName,
            'key': key
        }
        print('body: ', body)

        # push to SQS
        try:
            sqs_client.send_message(
                QueueUrl=sqsUrl, 
                MessageAttributes={},
                MessageDeduplicationId=eventId,
                MessageGroupId="putEvent",
                MessageBody=json.dumps(body)
            )

        except Exception as e:        
            print('Fail to delete the queue message: ', e)
        
        # update status from created to loaded in dynamodb
        Key = {
            'event_id': {'S':eventId},
            'event_timestamp': {'S':eventTimestamp}
        }

        body = json.dumps(eventBody)
        
        try:
            resp = dynamodb_client.update_item(
                TableName=tableName, 
                Key=Key, 
                UpdateExpression='SET event_status = :status',
                #UpdateExpression='SET event_status = :status, event_body = :body',
                ExpressionAttributeValues={
                    ':status': {'S': 'loaded'},
                    #':body': {'S': body}
                }
            )
        except Exception:
            err_msg = traceback.format_exc()
            print('err_msg: ', err_msg)
            raise Exception ("Not able to update in dynamodb") 
        #print('resp, ', resp)
    
    return {
        'statusCode': 200,
    }        