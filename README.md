# S3를 통해 들어오는 트래픽을 제어하는 Simple Load Manager

여기서는 S3를 통해 들어오는 다수의 트래픽의 로드를 분산하기 위한 간단한 Load Manager를 보여주고자 합니다. 이때의 전체적인 Architecture는 아래와 같습니다. 여기서 

<img width="806" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/81efa92b-ac45-404b-8fd4-f24d61987341">


## Load Manager가 필요한 이유

Load Manager를 사용하지 않은 일반적은 경우의 트래픽 처리는 아래와 같습니다. 

1) S3를 통해 다수의 파일들인 입입됩니다.
2) S3의 Object가 인입될때 발생하는 putEvnet를 Lambda가 받아서, S3 Object에 대한 bucket, key에 대한 정보를 수집합니다.
3) AWS StepFunctions의 처리 속도와 입력되는 데이터 속도를 맞추기 위하여 SQS에 S3 Object에 대한 정보를 저장합니다.
4) Lambda(Inovoke)는 SQS에서 event를 받아서 Step Functions에 전달합니다.

<img width="659" alt="image" src="https://github.com/kyopark2014/s3-event-load-manager/assets/52392004/bb65d6bc-e2ce-4a28-ab58-5dfae0731f82">

기본적인 Call Flow는 아래와 같습니다.


## Load Manager를 사용하는 경우

