# Lambda Docker 部署指南

本文档记录如何使用 Docker 容器镜像方式部署 Lambda 函数，解决 Windows 环境依赖不兼容问题。

## 前置要求

- AWS CLI 已配置
- Docker Desktop 已运行
- ECR 仓库已创建（或自动创建）

---

## 快速部署命令

### 完整部署流程

```powershell
# ========== 1. 环境配置 ==========
$ACCOUNT_ID = "664418983183"
$REGION = "ap-southeast-2"
$FUNCTION_NAME = "ai-news"
$ROLE_NAME = "ai-news-lambda-role"

# ========== 2. 登录 ECR ==========
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# ========== 3. 创建 IAM 角色 ==========
aws iam create-role `
  --role-name $ROLE_NAME `
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam attach-role-policy `
  --role-name $ROLE_NAME `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# 添加 Secrets Manager 权限
aws iam put-role-policy `
  --role-name $ROLE_NAME `
  --policy-name SecretsManagerAccess `
  --policy-document '{"Version":"2012-10-17":"Allow","Action":["secretsmanager","Statement":[{"Effect:*"],"Resource":["*"]}]}'

# ========== 4. 构建并推送镜像 ==========
# 使用 --provenance=false 避免 OCI 格式问题
docker buildx build --platform linux/amd64 -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$FUNCTION_NAME:latest . --provenance=false --push

# ========== 5. 首次创建函数 ==========
aws lambda create-function `
  --function-name $FUNCTION_NAME `
  --package-type Image `
  --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$FUNCTION_NAME:latest `
  --role arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME `
  --region $REGION

# ========== 6. 配置函数 ==========
# 设置超时和内存
aws lambda update-function-configuration `
  --function-name $FUNCTION_NAME `
  --timeout 300 `
  --memory-size 512 `
  --region $REGION

# 设置环境变量（Secrets Manager 模式）
aws lambda update-function-configuration `
  --function-name $FUNCTION_NAME `
  --environment "Variables={SECRETS_MANAGER_NAME=ai-news,LLM_MODEL=deepseek/deepseek-chat}" `
  --region $REGION

# ========== 7. 创建 Secrets ==========
aws secretsmanager create-secret `
  --name ai-news `
  --description "AI News Lambda secrets" `
  --secret-string '{"DEEPSEEK_API_KEY":"your-api-key","RESEND_API_KEY":"your-resend-key","EMAIL_TO":"your-email","EMAIL_FROM":"your-from-email","LLM_MODEL":"deepseek/deepseek-chat"}' `
  --region $REGION
```

---

## 更新部署（代码变更后）

```powershell
# 1. 重新构建并推送镜像
docker buildx build --platform linux/amd64 -t 664418983183.dkr.ecr.ap-southeast-2.amazonaws.com/ai-news:latest . --provenance=false --push

# 2. 更新 Lambda 代码
aws lambda update-function-code `
  --function-name ai-news `
  --image-uri 664418983183.dkr.ecr.ap-southeast-2.amazonaws.com/ai-news:latest `
  --region ap-southeast-2
```

---

## 测试 Lambda

```powershell
# 调用函数
aws lambda invoke `
  --function-name ai-news `
  --region ap-southeast-2 `
  --payload '{}' `
  response.json

# 查看响应
Get-Content response.json
```

---

## 查看日志

```powershell
# 查看最近的日志事件
aws logs filter-log-events `
  --log-group-name "/aws/lambda/ai-news" `
  --limit 50 `
  --region ap-southeast-2
```

---

## 关键说明

### 为什么需要 `--provenance=false`？

Docker 默认构建 OCI 格式镜像，但 AWS Lambda 只支持 Docker v2 manifest。添加 `--provenance=false` 可生成兼容格式。

### Dockerfile 示例

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY lambda_function.py .
COPY src/ ./src/

# Set working directory
WORKDIR /var/task

# Set handler
CMD ["lambda_function.lambda_handler"]
```

### 环境变量模式

| 模式 | 环境变量 | 说明 |
|------|----------|------|
| Secrets Manager | `SECRETS_MANAGER_NAME=ai-news` | 从 Secrets Manager 读取密钥 |
| 本地开发 | `IS_LOCAL=true` | 从环境变量直接读取 |

### Secrets Manager Secret 格式

```json
{
  "DEEPSEEK_API_KEY": "sk-xxx",
  "RESEND_API_KEY": "re_xxx",
  "EMAIL_TO": "email@example.com",
  "EMAIL_FROM": "sender@example.com",
  "LLM_MODEL": "deepseek/deepseek-chat"
}
```

---

## 常见问题

### Q: 镜像不被支持
```
The image manifest, config or layer media type for the source image is not supported.
```
**解决**: 使用 `docker buildx build --provenance=false`

### Q: Secrets 无法读取
```
User is not authorized to perform secretsmanager:GetSecretValue
```
**解决**: 确保 IAM 角色有 Secrets Manager 权限

### Q: 超时
**解决**: Lambda 默认超时 3 秒，需要设置为 300 秒
