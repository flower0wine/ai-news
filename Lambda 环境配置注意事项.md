# Lambda 环境配置与运行时设置

## 一、环境变量

### 1.1 基本配置

Lambda 支持在函数级别设置环境变量:

```bash
# AWS CLI 设置环境变量
aws lambda update-function-configuration \
  --function-name my-function \
  --Environment 'Variables={
    "ENVIRONMENT":"production",
    "LOG_LEVEL":"info"
  }'
```

### 1.2 敏感信息处理

**禁止**: 在环境变量中直接存储密钥、密码

**正确方式**:
1. 使用 AWS Secrets Manager
2. 使用 Parameter Store
3. 使用 KMS 加密

```python
import boto3
import json
import os

def handler(event, context):
    # 从 Secrets Manager 获取密钥
    secrets_client = boto3.client('secretsmanager')
    secret = secrets_client.get_secret_value(
        SecretId='my-api-key'
    )
    api_key = json.loads(secret['SecretString'])['api_key']
    
    # 从 Parameter Store 获取配置
    ssm = boto3.client('ssm')
    param = ssm.get_parameter(
        Name='/myapp/config-value',
        WithDecryption=True
    )
    config_value = param['Parameter']['Value']
```

### 1.3 环境变量加密

```bash
# 使用 KMS 加密
aws lambda update-function-configuration \
  --function-name my-function \
  --KMSKeyArn arn:aws:kms:region:account:key/key-id \
  --Environment 'Variables={"SECRET":"encrypted-value"}'
```

### 1.4 环境变量对冷启动的影响

- 设置环境变量会增加冷启动时间(约 20-100ms)
- 原因: Lambda 需要使用 KMS 解密环境变量
- 建议: 尽量减少环境变量数量

---

## 二、运行时版本

### 2.1 Python 运行时

| 版本 | 状态 | 备注 |
|------|------|------|
| Python 3.12 | 推荐 | 最新 LTS |
| Python 3.11 | 推荐 | 稳定 |
| Python 3.10 | 支持 | 即将 EOL |

### 2.2 Node.js 运行时

| 版本 | 状态 | 备注 |
|------|------|------|
| Node.js 22.x | 推荐 | 最新 LTS |
| Node.js 20.x | 推荐 | 稳定 |
| Node.js 18.x | 支持 | 即将 EOL |

**注意**: Node.js 24+ 不再支持 callback 风格的 handler

---

## 三、Memory 与 Timeout

### 3.1 Memory 配置

- **范围**: 128MB ~ 10,240MB (10GB)
- **与 CPU 关系**: Memory 越高，CPU 性能越强

```bash
# 设置 Memory
aws lambda update-function-configuration \
  --function-name my-function \
  --MemorySize 512
```

**推荐策略**:
- 小函数(简单逻辑): 128-256MB
- 中等函数(API 调用): 512-1024MB
- 大函数(数据处理): 1024MB+

### 3.2 Timeout 配置

- **默认**: 3 秒
- **最大**: 900 秒 (15 分钟)

```bash
# 设置 Timeout
aws lambda update-function-configuration \
  --function-name my-function \
  --Timeout 30
```

---

## 四、VPC 配置

### 4.1 何时使用 VPC

- 访问 RDS、VPC 内资源
- 访问私有资源
- 安全隔离需求

### 4.2 VPC 配置要求

```yaml
# SAM template 示例
MyFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: my-vpc-function
    VpcConfig:
      SecurityGroupIds:
        - !GetAtt SecurityGroup.GroupId
      SubnetIds:
        - !Ref SubnetA
        - !Ref SubnetB
    ...
```

### 4.3 网络配置注意事项

Lambda 在 VPC 中需要:
1. **ENI (Elastic Network Interface)**: 每个函数实例需要一个 ENI
2. **NAT Gateway**: 访问公网(可选)
3. **足够 IP**: 子网要有足够可用 IP

```bash
# 查看 VPC 配置的 Lambda 函数
aws lambda get-function-configuration \
  --function-name my-function \
  --query 'VpcConfig'
```

---

## 五、Cold Start 优化

### 5.1 Cold Start 原因

Cold start 发生在:
- 函数首次调用
- 函数长时间未调用(约 5-30 分钟)
- 并发请求超出预置实例数

### 5.2 Cold Start 组成

| 阶段 | 说明 |
|------|------|
| Init | 加载代码、创建执行环境 |
| Runtime | 启动运行时 |
| Function | 执行初始化代码 |

### 5.3 VPC 冷启动问题

- **额外开销**: 6-10 秒创建 ENI
- **原因**: Lambda 需要在 VPC 中创建网络接口
- **解决方案**: 使用 VPC Endpoint 或 NAT Gateway

### 5.4 优化策略

| 策略 | 效果 | 成本 |
|------|------|------|
| 预置并发 (Provisioned Concurrency) | 消除冷启动 | 高 |
| 减小部署包 | 减少 Init 时间 | 低 |
| 延迟加载依赖 | 减少初始化时间 | 低 |
| 避免 VPC | 减少网络配置开销 | 低 |
| 减少初始化代码 | 减少 Init 时间 | 低 |

```yaml
# SAM 中配置预置并发
MyFunction:
  Type: AWS::Serverless::Function
  Properties:
    ProvisionedConcurrencyConfig:
      ProvisionedConcurrentExecutions: 5
```

---

## 六、Ephemeral Storage (/tmp)

### 6.1 默认配置

- **默认大小**: 512MB
- **最大**: 10,240MB (10GB)
- **位置**: /tmp 目录
- **生命周期**: 仅在函数执行期间存在

### 6.2 配置方法

```bash
# AWS CLI 设置
aws lambda update-function-configuration \
  --function-name my-function \
  --EphemeralStorage '{"Size": 1024}'
```

### 6.3 常见用途

- 临时文件处理
- 机器学习模型缓存
- 大文件下载处理
- 临时数据缓存

### 6.4 注意事项

- **每次调用后清除**: 数据不持久化
- **加密**: 自动使用 AWS 管理的密钥加密
- **并发限制**: 不同执行环境不共享 /tmp

---

## 七、其他配置项

### 7.1 执行角色 (IAM Role)

```bash
# 指定执行角色
aws lambda update-function-configuration \
  --function-name my-function \
  --Role arn:aws:iam::account:role/lambda-role
```

### 7.2 层数限制

- 函数最多附加 5 个 Layer
- 所有 Layer 总大小限制: 50MB (未解压)

### 7.3 并发限制

```bash
# 设置保留并发
aws lambda put-function-concurrency \
  --function-name my-function \
  --ReservedConcurrentExecutions 10
```

### 7.4 Dead Letter Queue

```bash
# 配置 DLQ
aws lambda update-function-configuration \
  --function-name my-function \
  --DeadLetterConfig '{
    "TargetArn": "arn:aws:sqs:region:account:queue-name"
  }'
```
