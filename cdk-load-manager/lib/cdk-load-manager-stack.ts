import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import * as path from "path";
import * as logs from "aws-cdk-lib/aws-logs"
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';

const debug = false;
const projectName = "s3-event-manager"
const region = process.env.CDK_DEFAULT_REGION;   

export class CdkLoadManagerStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // s3 
    const s3Bucket = new s3.Bucket(this, `storage-for-${projectName}`, {
      bucketName: `storage-for-${projectName}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      publicReadAccess: false,
      versioned: false,
    });
    if (debug) {
      new cdk.CfnOutput(this, 'bucketName', {
        value: s3Bucket.bucketName,
        description: 'The nmae of bucket',
      });
      new cdk.CfnOutput(this, 's3Arn', {
        value: s3Bucket.bucketArn,
        description: 'The arn of s3',
      });
      new cdk.CfnOutput(this, 's3Path', {
        value: 's3://' + s3Bucket.bucketName,
        description: 'The path of s3',
      });
    }

    // SQS for S3 event
    const queueS3event = new sqs.Queue(this, 'queueS3event', {
      visibilityTimeout: cdk.Duration.seconds(120),
      queueName: "queue-s3-putEvent.fifo",
      fifo: true,
      contentBasedDeduplication: false,
      deliveryDelay: cdk.Duration.millis(0),
      retentionPeriod: cdk.Duration.days(2),
    });
    if (debug) {
      new cdk.CfnOutput(this, 'sqsS3PutEventUrl', {
        value: queueS3event.queueUrl,
        description: 'The url of the S3 putEvent Queue',
      });
    }

    // SQS for Invokation 
    const queueInvokation = new sqs.Queue(this, 'queueInvocation', {
      visibilityTimeout: cdk.Duration.seconds(120),
      queueName: "queue-Invocation.fifo",
      fifo: true,
      contentBasedDeduplication: false,
      deliveryDelay: cdk.Duration.millis(0),
      retentionPeriod: cdk.Duration.days(2),
    });
    if (debug) {
      new cdk.CfnOutput(this, 'sqsInvoationUrl', {
        value: queueInvokation.queueUrl,
        description: 'The url of the S3 Invoation Queue',
      });
    }

    const roleLambda = new iam.Role(this, `role-lambda-for-${projectName}`, {
      roleName: `role-lambda-${projectName}-${region}`,
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("lambda.amazonaws.com"),
      )
    });
    const sqsPolicy = new iam.PolicyStatement({  
      resources: ['*'],      
      actions: ['sqs:*'],
    });      
    roleLambda.attachInlinePolicy( 
      new iam.Policy(this, `lambda-inline-policy-for-${projectName}`, {
        statements: [sqsPolicy],
      }),
    ); 

    // Lambda for s3 event
    const lambdaS3event = new lambda.Function(this, `lambda-s3-event-for-${projectName}`, {
      description: 'lambda for s3 event',
      functionName: `lambda-s3-event-for-${projectName}`,
      handler: 'lambda_function.lambda_handler',
      runtime: lambda.Runtime.PYTHON_3_11,
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda-s3-event')),
      timeout: cdk.Duration.seconds(120),
      role: roleLambda,
      logRetention: logs.RetentionDays.ONE_DAY,
      environment: {
        queueS3event: queueS3event.queueUrl
      }
    });
    s3Bucket.grantReadWrite(lambdaS3event); // permission for s3
    queueS3event.grantSendMessages(lambdaS3event); // permision for SQS putEvent
    
    // s3 put event source
    const s3PutEventSource = new lambdaEventSources.S3EventSource(s3Bucket, {
      events: [
        s3.EventType.OBJECT_CREATED_PUT,
      ],
      filters: [
        { prefix: 'data/' },
      ]
    });
    lambdaS3event.addEventSource(s3PutEventSource);        

    // Lambda for schedular
    const lambdaSchedular = new lambda.Function(this, `lambda-schedular-${projectName}`, {
      description: 'lambda for schedular',
      functionName: `lambda-schedular-for-${projectName}`,
      handler: 'lambda_function.lambda_handler',
      runtime: lambda.Runtime.PYTHON_3_11,
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda-schedular')),
      timeout: cdk.Duration.seconds(120),
      logRetention: logs.RetentionDays.ONE_DAY,
      environment: {
        eventSqsUrl: queueS3event.queueUrl,
        invokationSqsUrl: queueInvokation.queueUrl
      }
    });
    queueS3event.grantSendMessages(lambdaSchedular); // permision for SQS putEvent
    queueInvokation.grantSendMessages(lambdaSchedular); // permision for SQS Invokation

    // cron job - EventBridge
    const rule = new events.Rule(this, `EventBridge-${projectName}`, {
      description: "rule-of-event-bridge",
      schedule: events.Schedule.expression('rate(1 minute)'),
    }); 
    rule.addTarget(new targets.LambdaFunction(lambdaSchedular)); 

    // Lambda - Invoke
    const lambdaInvoke = new lambda.Function(this, `lambda-invoke-for-${projectName}`, {
      description: 'lambda for invoke',
      functionName: `lambda-invoke-for-${projectName}`,
      handler: 'lambda_function.lambda_handler',
      runtime: lambda.Runtime.PYTHON_3_11,
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda-invoke')),
      timeout: cdk.Duration.seconds(120),
      logRetention: logs.RetentionDays.ONE_DAY,
      environment: {
        invokationSqsUrl: queueInvokation.queueUrl
      }
    });
    // grant permissions
    s3Bucket.grantRead(lambdaInvoke);  // read permission for S3
    lambdaInvoke.addEventSource(new SqsEventSource(queueS3event)); // permission for SQS

    // copy commend
    new cdk.CfnOutput(this, 'copyCommend', {
      value: `aws s3 cp ~/environment/data/ s3://${s3Bucket.bucketName}/data/ --recursive`,
      description: 'The copy commend',
    });
  }
}
