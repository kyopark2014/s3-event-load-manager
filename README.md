# S3의 Object 부하를 제어하는 Simple Load Manager

여기서는 S3를 통해 들어오는 다수의 트래픽의 로드를 분산하기 위한 간단한 Load Manager를 보여주고자 합니다. 이때의 전체적인 Architecture는 아래와 같습니다. 여기서 EventBridge는 Load 분산을 위하여 일정시간 간격으로 Lambda(schedular)를 호출합니다. Lambda(schedular)는 SQS(event)에서 Step Functions가 한번에 처리가능한 수량의 Event를 가져와서 SQS(invokation)에 옮겨 놓습니다. SQS(invokation)로 들어온 Event은 Lambda(invoke)에 전달되어, Step Functions에 순차적으로 실행하게 됩니다.

<img width="800" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/d2f1c58e-9abf-443d-a82b-56d3e27ace1f">

이때의 Call Flow는 아래와 같습니다.

1) EKS에서 다수의 데이터를 S3에 object로 저장합니다. 
2) S3에 object가 인입될때 발생하는 put evnet를 Lambda(S3-event)가 받아서, S3 Object에 대한 bucket, key에 대한 정보를 수집합니다.
3) Lambda(S3-event)는 object에 대한 정보를 SQS(event)에 push 합니다.
4) 정기적으로 EventBridge는 Lambda(schedular)를 Trigger합니다.
5) Lambda(Schedular)는 SQS(event)에서 N개의 메시지를 읽어오고, 읽어온 메시지는 삭제합니다. 여기서 N은 StepFunctions가 처리하는 그룹 작업(job)의 숫자입니다.
6) Lambda(Schedular)는 SQS(invocation)에 N개의 메시지를 push 합니다.
7) SQS(invocation)가 Lambda(invoke)를 trigger합니다.
8) Lambda(Inovoke)는 Step Functions을 실행해야 Job을 수행합니다.
   
<img width="800" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/9dd23b6a-7c92-4302-86c2-fd99fdf90067">


## Load Manager가 필요한 이유

Load Manager를 사용하지 않은 일반적은 경우의 트래픽 처리는 아래와 같습니다. 

1) S3를 통해 다수의 파일들인 인입됩니다.
2) S3의 Object가 인입될때 발생하는 put evnet를 Lambda (S3-event)가 받아서, Object에 대한 bucket, key에 대한 정보를 추출합니다.
3) AWS StepFunctions의 처리 속도와 입력되는 데이터 속도를 맞추기 위하여 SQS에 S3 Object에 대한 정보를 저장합니다.
4) Lambda(Inovoke)는 SQS에서 event를 받아서 Step Functions에 전달합니다.

이러한 event driven architecture는 유연한 시스템을 구성하는데 많은 도움을 주지만, 실제 프로세싱을 하는 Step Function으로 인입되는 트래픽을 정밀하게 제어하기 어렵습니다. 예를 들면, S3로 인입되는 다수의 Data 처리를 한꺼번에 Step Function에서 처리할 수 없는 경우에 50개 또는 100개 단위로 5분간격으로 처리하고자 한다면, 스케줄러를 이용하여야 합니다.

<img width="700" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/47f9174e-e7a7-4a59-90f2-1d58ee322fa8">



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

[Lambda (schedular)](./lambda-schedular/lambda_function.py) 는 EventBrdige의 trigger를 받아서, SQS(event)로 부터 N개의 처리 가능한 수량의 메시지를 읽어서, SQS(Invocation)에 전달합니다. EventBridge가 Lambda(schedular)를 trigger하면 아래와 같이 receive_message를 이용하여 10개씩 메시지를 읽어옵니다. 참고로 receive_message()가 한번에 읽어올수 있는 메시지는 최대 10개입니다.

EventBridge가 처리할 수 있는 job의 갯수를 capacity라고 정의하였습니다. 아래와 같이 receive_message()를 이용하여 SQS(invoke)에서 메시지를 읽어오는데, 읽어온 메시지의 전체 숫자가 capacity보다 크다면 읽어오는 동작을 멈춥니다. 만약 읽어온 메시지의 숫자가 capacity보다 작다면, SQS(event)에서 10개씩 메시지를 읽어서 SQS(invokation)에 push합니다. SQS(event)에 더이상 메시지 없으면 읽어오는 동작을 멈춥니다.

```python
while True:
    if cnt > capacity:
        break

    try:               
        sqsReceiveResponse = sqs_client.receive_message(
            QueueUrl=eventSqsUrl,
            MaxNumberOfMessages=10,
        )
            
        number_of_message = len(sqsReceiveResponse.get('Messages', []))
            if number_of_message==0:
                break
```

읽어들인 메시지는 SQS(invokation)으로 push하고 SQS(event)의 메시지는 삭제합니다.

```python
for message in sqsReceiveResponse.get("Messages", []):
    message_body = message["Body"]
    receiptHandle = message['ReceiptHandle']

    jsonbody = json.loads(message_body)
    try:
        sqs_client.send_message(
        QueueUrl = invocationSqsUrl,
        MessageAttributes = {},
        MessageDeduplicationId = jsonbody['event_id'],
        MessageGroupId = "invokation",
        MessageBody = message_body
    )
    except Exception as e:
        print('Fail to push the queue message: ', e)

    try:
        sqs_client.delete_message(
            QueueUrl = eventSqsUrl,
            ReceiptHandle = receiptHandle
        )
        except Exception as e:
            print('Fail to delete the queue message: ', e)
```


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


SQS(event)에 아래와 같이 13:14분에 115개의 메시지가 수신되었습니다. 
ㄴ
![image](https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/cac72a09-95ff-499e-b60d-1fa307d2b13b)

SQS(invokation)에서 Lambda(invoke)로 전달된 메시지는 아래와 같이 3번에 나누어서 전달되었습니다.

![image](https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/fbaa52ed-ee15-4675-b379-d7ffaca274a9)
