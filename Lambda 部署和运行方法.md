# Lambda 部署与运行指南

## 一、部署方式

### 1.1 AWS Console

适用于快速测试和简单函数:

1. 打开 AWS Lambda Console
2. 创建函数或上传代码
3. 配置触发器和环境变量
4. 部署

**限制**: 不适合生产环境的自动化部署

### 1.2 AWS CLI

```bash
# 创建函数
aws lambda create-function \
  --function-name my-function \
  --runtime python3.12 \
  --role arn:aws:iam::account:role/lambda-role \
  --handler lambda_function.handler \
  --zip-file fileb://function.zip

# 更新函数代码
aws lambda update-function-code \
  --function-name my-function \
  --zip-file fileb://function.zip \
  --publish

# 更新函数配置
aws lambda update-function-configuration \
  --function-name my-function \
  --MemorySize 512 \
  --Timeout 30
```

### 1.3 AWS SAM (Serverless Application Model)

**SAM Template 示例**:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: my-sam-function
      Runtime: python3.12
      Handler: app.handler
      CodeUri: ./
      MemorySize: 512
      Timeout: 30
      Environment:
        Variables:
          ENVIRONMENT: production
      Layers:
        - !Ref MyLayer

  MyLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: my-common-layer
      ContentUri: ./layer/
      CompatibleRuntimes:
        - python3.12
```

**部署命令**:

```bash
# 本地构建
sam build

# 本地测试
sam local invoke MyFunction --event event.json
sam local start-api

# 部署
sam deploy --guided
```

### 1.4 AWS CDK

```python
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
)
from constructs import Construct

class MyLambdaStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # 创建 Lambda 函数
        function = _lambda.Function(
            self, "MyFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="app.handler",
            code=_lambda.Code.from_asset("lambda/"),
            memory_size=512,
            timeout=Duration.seconds(30),
        )
        
        # 添加 Layer
        layer = _lambda.LayerVersion(
            self, "MyLayer",
            code=_lambda.Code.from_asset("layer/"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
        )
        function.add_layers(layer)
```

**部署命令**:

```bash
cdk deploy
cdk synth  # 生成 CloudFormation 模板
```

### 1.5 Serverless Framework

```yaml
service: my-service

provider:
  name: aws
  runtime: python3.12
  memorySize: 512
  timeout: 30
  environment:
    ENVIRONMENT: production

functions:
  hello:
    handler: handler.hello
    events:
      - http:
          path: hello
          method: get
  layers:
    - arn:aws:lambda:region:account:layer:my-layer:1
```

**部署命令**:

```bash
serverless deploy
serverless invoke -f hello --log
```

---

## 二、本地测试

### 2.1 SAM CLI 安装

```bash
# macOS
brew install aws-sam-cli

# Linux
pip install aws-sam-cli

# Windows
choco install aws-sam-cli

# 验证
sam --version
```

**前置要求**: Docker Desktop 必须运行

### 2.2 本地调用函数

```bash
# 使用事件文件调用
sam local invoke MyFunction --event event.json

# 指定环境变量
sam local invoke MyFunction \
  --event event.json \
  --env-vars env.json

# 使用 Docker 网络模式
sam local invoke MyFunction --event event.json \
  --docker-network host
```

**event.json 示例**:

```json
{
  "body": "{\"message\": \"hello\"}",
  "httpMethod": "POST",
  "path": "/items",
  "queryStringParameters": {
    "id": "123"
  }
}
```

### 2.3 本地启动 API Gateway

```bash
# 启动本地 API
sam local start-api

# 指定端口
sam local start-api --port 3000

# 自动 reload
sam local start-api --warm-containers lazy
```

### 2.4 Layer 本地测试

```bash
# 指定 Layer
sam local invoke MyFunction \
  --event event.json \
  --layer arn:aws:lambda:region:account:layer:my-layer:1
```

---

## 三、Lambda@Edge 与容器镜像

### 3.1 Lambda@Edge

在 CloudFront 边缘节点运行 Lambda:

**使用场景**:
- 请求/响应拦截
- URL 重写
- A/B 测试
- 访问控制

```yaml
# CloudFront 触发器
Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: index.handler
      Runtime: nodejs20.x
      CodeUri: ./
      Description: "Edge function"
      Timeout: 30

  CloudFrontTrigger:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        DefaultCacheBehavior:
          LambdaFunctionAssociations:
            - EventType: origin-request
              LambdaFunctionARN: !GetAtt MyFunction.Arn
```

**限制**:
- 仅支持 Node.js 和 Python
- 超时最长 30 秒
- 内存最大 128MB

### 3.2 容器镜像部署

适用于大型依赖或自定义运行时:

```dockerfile
# Python 示例
FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./

CMD ["app.handler"]
```

```dockerfile
# Node.js 示例
FROM public.ecr.aws/lambda/nodejs:20

WORKDIR /var/task

COPY package*.json ./
RUN npm install --production

COPY . .

CMD ["index.handler"]
```

**构建与部署**:

```bash
# 构建
docker build -t my-function .

# 本地测试
docker run -p 9000:8080 my-function
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"key": "value"}'

# 推送到 ECR
docker tag my-function $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/my-function:latest
docker push $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/my-function:latest

# 创建函数
aws lambda create-function \
  --function-name my-function \
  --package-type Image \
  --code ImageUri=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/my-function:latest \
  --role role-arn
```

---

## 四、版本与别名

### 4.1 版本概念

- `$LATEST`: 开发版本，可编辑
- 数字版本: 每次发布创建新版本

```bash
# 发布新版本
aws lambda publish-version \
  --function-name my-function \
  --description "Release v1.0"

# 查看版本
aws lambda list-versions-by-function \
  --function-name my-function
```

### 4.2 别名管理

别名指向特定版本:

```bash
# 创建别名
aws lambda create-alias \
  --function-name my-function \
  --name production \
  --function-version 1 \
  --description "Production alias"

# 更新别名指向
aws lambda put-function-event-invoke-config \
  --function-name my-function \
  --alias-name production \
  --destination-config '{
    "OnFailure": {
      "Destination": "arn:aws:sqs:region:account:dlq"
    }
  }'
```

### 4.3 流量转移

```bash
# 使用 weighted alias 实现蓝绿部署
aws lambda update-alias \
  --function-name my-function \
  --name production \
  --routing-configure-additional-version '{
    "AdditionalVersionWeights": {
      "2": 0.1
    }
  }'
```

---

## 五、调用类型

### 5.1 同步调用 (RequestResponse)

- 等待函数返回结果
- 超时则失败

```bash
aws lambda invoke \
  --function-name my-function \
  --invocation-type RequestResponse \
  --payload '{"key": "value"}' \
  response.json
```

### 5.2 异步调用 (Event)

- 立即返回，不等待结果
- Lambda 自动重试 2 次

```bash
aws lambda invoke \
  --function-name my-function \
  --invocation-type Event \
  --payload '{"key": "value"}' \
  response.json
```

### 5.3 DryRun 验证

- 仅验证权限，不执行函数

```bash
aws lambda invoke \
  --function-name my-function \
  --invocation-type DryRun \
  --payload '{}' \
  response.json
```

---

## 六、错误处理与重试

### 6.1 事件源重试行为

| 事件源 | 重试次数 | 间隔 |
|--------|----------|------|
| API Gateway | 0 (返回 502) | - |
| S3 | 2 次 | 指数退避 |
| SQS | 保留消息 | 到达后立即重试 |
| DynamoDB Streams | 无限* | 直到成功或过期 |
| SNS | 多次 | 指数退避 |

### 6.2 Dead Letter Queue (DLQ)

配置 DLQ 收集失败事件:

```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --DeadLetterConfig '{
    "TargetArn": "arn:aws:sqs:region:account:queue-name"
  }'
```

### 6.3 Destinations (推荐)

```bash
aws lambda put-function-event-invoke-config \
  --function-name my-function \
  --destination-config '{
    "OnSuccess": {
      "Destination": "arn:aws:sqs:region:account:success-queue"
    },
    "OnFailure": {
      "Destination": "arn:aws:sqs:region:account:failure-queue"
    }
  }'
```

### 6.4 自定义重试逻辑

```python
import time
import random

def handler(event, context):
    max_retries = 3
    attempt = 0
    
    while attempt < max_retries:
        try:
            # 业务逻辑
            result = call_external_api(event)
            return {"statusCode": 200, "body": result}
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                # 记录到 DLQ 或抛出异常触发重试
                raise e
            # 指数退避 + 抖动
            sleep_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(sleep_time)
```

---

## 七、最佳实践

### 7.1 部署最佳实践

- 使用基础设施即代码 (IaC): SAM/CDK/Serverless
- 分离开发和生产环境: 使用 Stage/别名
- 自动化测试: CI/CD 流程
- 小型部署包: 使用 Layers

### 7.2 测试最佳实践

- 本地测试: SAM CLI + Docker
- 集成测试: 使用 SAM local start-api
- 单元测试: pytest/jest
- 端到端测试: 部署到测试环境

### 7.3 监控与调试

```bash
# 查看日志
aws logs tail /aws/lambda/my-function --follow

# 查看指标
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### 7.4 CI/CD 集成示例

```yaml
# GitHub Actions
name: Deploy Lambda

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Build and Deploy
        run: |
          sam build
          sam deploy --no-confirm-changeset
```
