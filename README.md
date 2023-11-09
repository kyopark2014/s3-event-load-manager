# S3의 Object 부하를 제어하는 Simple Load Manager

여기서는 S3를 통해 들어오는 다수의 트래픽의 로드를 분산하기 위한 간단한 Load Manager를 보여주고자 합니다. 이때의 전체적인 Architecture는 아래와 같습니다. 여기서 EventBridge는 Load 분산을 위하여 일정시간 간격으로 Lambda(schedular)를 호출합니다. Lambda(schedular)는 SQS(event)에서 Step Functions가 한번에 처리가능한 수량의 Event를 가져와서 SQS(invokation)에 옮겨 놓습니다. SQS(invokation)로 들어온 Event은 Lambda(invoke)에 전달되어, Step Functions에 순차적으로 실행하게 됩니다.

<img width="806" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/d2f1c58e-9abf-443d-a82b-56d3e27ace1f">

이때의 Call Flow는 아래와 같습니다.

1) S3를 통해 다수의 파일들인 입입됩니다.
2) S3의 Object가 인입될때 발생하는 put Evnet를 Lambda(S3-event)가 받아서, S3 Object에 대한 bucket, key에 대한 정보를 수집합니다.
3) Lambda(S3-event)는 Object에 대한 정보를 SQS(event)에 push 합니다.
4) 정기적으로 EventBridge는 Labmda(schedular)를 Trigger합니다.
5) Lambda(Schedular)는 SQS(event)에서 N개의 메시지를 읽어오고, 읽어온 메시지는 삭제합니다.
6) Lambda(Schedular)는 SQS(invocation)에 N개의 메시지를 push 합니다.
7) SQS(invocation)이 Lambda(invoke)에 event로 object에 대한 정보는 전달합니다.
9) Lambda(Inovoke)이 Step Functions에 실행해야할 Job에 대한 정보를 전달합니다. 이후, Step Functions는 주어진 동작을 수행합니다.
   
<img width="806" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/9dd23b6a-7c92-4302-86c2-fd99fdf90067">


## Load Manager가 필요한 이유

Load Manager를 사용하지 않은 일반적은 경우의 트래픽 처리는 아래와 같습니다. 

1) S3를 통해 다수의 파일들인 입입됩니다.
2) S3의 Object가 인입될때 발생하는 putEvnet를 Lambda (S3-event)가 받아서, Object에 대한 bucket, key에 대한 정보를 추출합니다.
3) AWS StepFunctions의 처리 속도와 입력되는 데이터 속도를 맞추기 위하여 SQS에 S3 Object에 대한 정보를 저장합니다.
4) Lambda(Inovoke)는 SQS에서 event를 받아서 Step Functions에 전달합니다.

이러한 event driven architecture는 유연한 시스템을 구성하는데 많은 도움을 주지만, 실제 프로세싱을 하는 Step Function으로 인입되는 트래픽을 정밀하게 제어하기 어렵습니다. 예를 들면, S3로 인입되는 다수의 Data 처리를 한꺼번에 Step Function에서 처리할 수 없는 경우에 50개 또는 100개 단위로 5분간격으로 처리하고자 한다면, 스케줄러를 이용하여야 합니다.

<img width="806" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/47f9174e-e7a7-4a59-90f2-1d58ee322fa8">



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
