# S3의 Object 부하를 제어하는 Simple Load Manager

여기서는 S3를 통해 들어오는 다수의 트래픽의 로드를 분산하기 위한 간단한 Load Manager를 보여주고자 합니다. 이때의 전체적인 Architecture는 아래와 같습니다. 여기서 EventBridge는 일정시간 간격으로 Load Mananaging을 수행하는 Lambda를 호출합니다. Lambda는 SQS에서 처리가능한 수량의 Event를 가져와서 Serving을 위한 SQS에 옮겨 놓습니다. Serving SQS르 들어온 Event은 Step Functions에 순차적으로 전달됩니다.

<img width="806" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/81efa92b-ac45-404b-8fd4-f24d61987341">


## Load Manager가 필요한 이유

Load Manager를 사용하지 않은 일반적은 경우의 트래픽 처리는 아래와 같습니다. 

1) S3를 통해 다수의 파일들인 입입됩니다.
2) S3의 Object가 인입될때 발생하는 putEvnet를 Lambda가 받아서, S3 Object에 대한 bucket, key에 대한 정보를 수집합니다.
3) AWS StepFunctions의 처리 속도와 입력되는 데이터 속도를 맞추기 위하여 SQS에 S3 Object에 대한 정보를 저장합니다.
4) Lambda(Inovoke)는 SQS에서 event를 받아서 Step Functions에 전달합니다.

이러한 event driven architecture는 유연한 시스템을 구성하는데 많은 도움을 주지만, 실제 프로세싱을 하는 Step Function으로 인입되는 트래픽을 정밀하게 제어하기 어렵습니다. 예를 들면, S3로 인입되는 다수의 Data 처리를 한꺼번에 Step Function에서 처리할 수 없는 경우에 50개 또는 100개 단위로 5분간격으로 처리하고자 한다면, 스케줄러를 이용하여야 합니다.

<img width="659" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/bb65d6bc-e2ce-4a28-ab58-5dfae0731f82">

기본적인 Call Flow는 아래와 같습니다.

![image](https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/1ad4ad93-72b2-4928-a38c-be78426023a7)


## Load Manager를 사용하는 경우

### S3의 Event 처리 

[Lambda (S3-event)](./lambda-s3-event/lambda_function.py) 는 S3에 Object가 생성될때 발생하는 S3 put Evnet를 받아서 SQS(S3-event)에 저장합니다. 

아래와 같이 [Lambda (S3-event)](./lambda-s3-event/lambda_function.py) 로 들어온 event에서 object의 bucket 이름과 key를 추출합니다.

```python
for record in event['Records']:
  print("record: ", record)

  s3 = record['s3']
  bucketName = s3['bucket']['name']
  key = s3['object']['key']
```

아래에서는 편의상 event ID로 uuid를 사용하고, timestamp를 지정하였습니다. 각 event의 body에는 object에 정보인 bucket과 key를 입력하고 SQS(S3-event)를 메시지로 넣습니다.

```python
eventId = str(uuid.uuid1())

d = datetime.datetime.now()
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
        
try:
    sqs_client.send_message(
        QueueUrl = sqsUrl,
        MessageAttributes = {},
        MessageDeduplicationId = eventId,
        MessageGroupId = "putEvent",
        MessageBody = json.dumps(s3EventInfo)
    )
```

### Event Schedular

[Lambda (schedular)](./lambda-schedular/lambda_function.py) 는 EventBrdige의 Trigger를 받아서, SQS(S3-event)로 부터 N개의 처리 가능한 수량의 메시지를 읽어서, SQS(Invocation)에 전달합니다.

## 인프라 설치

[deployment.md](./deployment.md)에 인프라를 설치하고 필요한 셈플 파일을 다운로드 합니다.

설치가 다 완료가 되면 아래와 같이 파일 복사 명령어를 확인할 수 있습니다.

<img width="1058" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/856b8d4c-e394-4b27-a709-e31592e6c87a">


## 실행 방법

Cloud9의 터미널에서 아래 명령어를 이용하여 S3의 data 폴더에 다량의 parquet 파일을 전송합니다.

```text
aws s3 cp ~/environment/data/ s3://storage-for-s3-event-manager/data/ --recursive
```

이후 CloudWatch에서 메시지가 순차적으로 처리되고 있는지 확인합니다.
