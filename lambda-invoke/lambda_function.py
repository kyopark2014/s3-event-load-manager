import json
import boto3
import os
import traceback
import datetime

s3 = boto3.client('s3')
sqs = boto3.client('sqs')
sqsUrl = os.environ.get('sqsUrl')
tableName = os.environ.get('tableName')
dynamodb_client = boto3.client('dynamodb')

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
        
        eventId = jsonbody['eventId']
        print("eventId: ", eventId)

        eventTimestamp = jsonbody['eventTimestamp']
        print("eventTimestamp: ", eventTimestamp)

        bucketName = jsonbody['bucketName']
        print("bucketName: ", bucketName)

        key = jsonbody['key']
        print("key: ", key)

        # delete queue
        try:
            sqs.delete_message(QueueUrl=sqsUrl, ReceiptHandle=receiptHandle)
        except Exception as e:        
            print('Fail to delete the queue message: ', e)
        
        
         # update status from created to loaded in dynamodb
        Key = {
            'event_id': {'S':eventId},
            'event_timestamp': {'S':eventTimestamp}
        }

        d = datetime.datetime.now()
        # timestamp = str(d)[0:19]  # min
        timestamp = str(d)
        body = json.dumps({
            'bucket_name': {'S':bucketName},
            'key': {'S':key}
        }) 

        try:
            resp = dynamodb_client.update_item(
                TableName=tableName, 
                Key=Key, 
                #UpdateExpression='SET event_status = :status',
                #UpdateExpression='SET event_status = :status, event_body = :body',
                UpdateExpression='SET event_status = :status, event_end = :event_end',

                ExpressionAttributeValues={
                    ':status': {'S': 'completed'},
                    #':body': {'S': body}
                    ':event_end': {'S': timestamp}                    
                }
            )
        except Exception:
            err_msg = traceback.format_exc()
            print('err_msg: ', err_msg)
            raise Exception ("Not able to update in dynamodb") 
        print('resp, ', resp)
        print('The status was upaded from loaded to completed: , ', eventId)

        # delete dynamodb
        #Key = {
        #    'event_id': {'S':eventId},
        #    'event_timestamp': {'S':eventTimestamp}
        #}
        
        #try:
        #    resp = dynamodb_client.delete_item(TableName=tableName, Key=Key)
        #except Exception:
        #    err_msg = traceback.format_exc()
        #    print('err_msg: ', err_msg)
        #    raise Exception ("Not able to write into dynamodb") 
        #print('resp, ', resp)
            
    statusCode = 200
    return {
        'statusCode': statusCode,
    }