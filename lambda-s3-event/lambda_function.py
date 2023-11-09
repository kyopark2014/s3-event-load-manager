import json
import boto3
import os
import datetime
import uuid
import traceback

tableName = os.environ.get('tableName')

def lambda_handler(event, context):
    print(event)

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
            'bucket_name': {'S':bucketName},
            'key': {'S':key}
        }) 
        
        item = {
            'event_id': {'S':eventId},
            'event_timestamp': {'S':timestamp},
            'event_end': {'S':'NA'},
            'event_status': {'S':'created'},  
            'event_body': {'S':body}     
        }
        
        client = boto3.client('dynamodb')
        try:
            resp = client.put_item(TableName=tableName, Item=item)
        except Exception as ex:
            err_msg = traceback.format_exc()
            print('err_msg: ', err_msg)
            raise Exception ("Not able to write into dynamodb")        
        print('resp, ', resp)

        s3eventInfo.append({
            'bucketName': bucketName,
            'key': key
        })
        
    return {
        'statusCode': 200,
        'result': json.dumps(s3eventInfo),
    }        