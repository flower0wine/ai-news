# AI News Lambda

自动化 AI 新闻摘要邮件服务。

## 功能

每天自动获取 AI 新闻，使用 LLM 总结后通过邮件发送给订阅者。

## 工作流程

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────┐
│  AlphaSignal    │───▶│  LLM 摘要生成     │───▶│   Resend    │
│  API 获取新闻   │    │  (DeepSeek)      │    │   发送邮件  │
└─────────────────┘    └──────────────────┘    └─────────────┘
```

1. 从 AlphaSignal API 获取最新 AI 新闻
2. 将 HTML 内容转换为 Markdown
3. 使用 LLM 生成新闻摘要
4. 通过 Resend 发送邮件给订阅者

## 技术栈

- **运行时**: AWS Lambda (Python 3.12)
- **部署**: Docker 容器镜像
- **LLM**: DeepSeek / Volcengine
- **邮件**: Resend
- **触发器**: EventBridge (每天北京时间 8:00)

## 项目结构

```
.
├── lambda_function.py    # Lambda 入口函数
├── src/
│   ├── config.py         # 配置管理
│   ├── api_client.py     # AlphaSignal API 客户端
│   ├── converter.py      # HTML 转 Markdown
│   ├── llm.py            # LLM 服务
│   └── email_sender.py   # 邮件发送
├── requirements.txt       # Python 依赖
├── Dockerfile            # Docker 镜像构建
└── template.yaml         # SAM 模板
```

## 配置

### 环境变量

| 变量 | 说明 | 来源 |
|------|------|------|
| `SECRETS_MANAGER_NAME` | Secrets Manager 密钥名 | 环境变量 |
| `LLM_MODEL` | LLM 模型名称 | 环境变量 |

### Secrets Manager 密钥格式

```json
{
  "DEEPSEEK_API_KEY": "sk-xxx",
  "RESEND_API_KEY": "re_xxx",
  "EMAIL_FROM": "sender@example.com",
  "EMAIL_TO": "recipient@example.com",
  "LLM_MODEL": "deepseek/deepseek-chat"
}
```

## 本地开发

```bash
# 1. 复制配置模板
cp .env.local.example .env.local

# 2. 编辑 .env.local，填写你的 API Keys

# 3. 安装依赖 (可选，用于本地 IDE 提示)
pip install -r requirements.txt

# 4. 运行测试
python lambda_function.py
```

## 部署

详见 [LAMBDA_DOCKER_DEPLOY.md](./LAMBDA_DOCKER_DEPLOY.md)

### Docker 部署

```powershell
# 构建并推送镜像
docker buildx build --platform linux/amd64 -t 664418983183.dkr.ecr.ap-southeast-2.amazonaws.com/ai-news:latest . --provenance=false --push

# 更新 Lambda
aws lambda update-function-code --function-name ai-news --image-uri 664418983183.dkr.ecr.ap-southeast-2.amazonaws.com/ai-news:latest
```

## 许可

MIT
