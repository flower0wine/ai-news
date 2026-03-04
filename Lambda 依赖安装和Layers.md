# Lambda 依赖安装与 Layers 使用指南

## 一、依赖安装基础

### 1.1 Python 依赖安装

Lambda 函数需要第三方库时，必须将依赖打包到部署包中。

```bash
# 方法1: pip 安装到本地目录
pip install -r requirements.txt -t ./package

# 打包
cd package && zip -r ../function.zip . && cd ..
zip -r function.zip lambda_function.py
```

**关键点**:
- 使用 `--target` 或 `-t` 指定安装目录
- 包含原生二进制包( numpy, pandas, psycopg2)需要在 Amazon Linux 2 环境构建
- Windows/Mac 用户建议使用 Docker 构建兼容包

```bash
# 使用 Docker 构建兼容 Amazon Linux 的包
docker run -v "$PWD":/var/task public.ecr.aws/lambda/python:3.12 \
  pip install -r requirements.txt -t /var/task/package
```

### 1.2 Node.js 依赖安装

```bash
npm install --prefix ./package

# 打包
cd package && zip -r ../function.zip . && cd ..
zip -r function.zip index.js
```

---

## 二、Lambda Layers 详解

### 2.1 什么是 Lambda Layers

Lambda Layers 是可复用的依赖包，包含:
- 共享库和 SDK
- 自定义运行时
- 配置文件、证书

**优势**:
- 减少每个函数的部署包大小
- 统一管理共享依赖
- 独立更新 Layer 不影响函数代码

### 2.2 Layer 目录结构

Lambda 自动将 Layer 内容解压到 `/opt` 目录:

| 运行时 | 自动添加到 Path 的路径 |
|--------|----------------------|
| Python | /opt/python/lib/python3.x/site-packages |
| Node.js | /opt/node_modules |

**手动引用**:
```python
import sys
sys.path.append('/opt/custom/lib')
```

### 2.3 创建与发布 Layer

**Step 1: 准备目录结构**

```bash
# Python Layer
mkdir -p python/lib/python3.12/site-packages
pip install requests -t python/lib/python3.12/site-packages
zip -r python-layer.zip python/
```

**Step 2: 发布 Layer**

```bash
aws lambda publish-layer-version \
  --layer-name my-common-layer \
  --zip-file fileb://python-layer.zip \
  --compatible-runtimes python3.12
```

**Step 3: 关联到函数**

```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:region:account:layer:my-common-layer:1
```

### 2.4 Layer 版本管理

- Layer 每个版本 immutable
- 更新依赖需发布新版本
- 函数可锁定到特定版本

---

## 三、部署包创建

### 3.1 ZIP 部署包

**Python 函数结构**:
```
function.zip
├── lambda_function.py    # 入口文件
└── package/              # 依赖目录
    ├── requests/
    └── boto3/
```

**Node.js 函数结构**:
```
function.zip
├── index.js              # 入口文件
└── node_modules/         # 依赖目录
```

### 3.2 容器镜像部署

适用于大型依赖或自定义运行时:

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py ./

CMD ["app.handler"]
```

**构建并推送**:
```bash
aws ecr get-login-password --region region | \
  docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.region.amazonaws.com

docker build -t my-function .
docker tag my-function $ACCOUNT.dkr.ecr.region.amazonaws.com/my-function:latest
docker push $ACCOUNT.dkr.ecr.region.amazonaws.com/my-function:latest
```

---

## 四、依赖管理最佳实践

### 4.1 推荐策略

| 场景 | 方案 |
|------|------|
| 少量函数，独立依赖 | 打包到函数部署包 |
| 多个函数，共享依赖 | 使用 Lambda Layers |
| 大型依赖(ML/数据处理) | 容器镜像 |
| 频繁更新的依赖 | 独立 Layer |

### 4.2 常见问题

**Q: 遇到 "No module named xxx" 错误**
- 检查 Layer 是否正确附加
- 验证目录结构是否符合规范

**Q: 原生库不兼容**
- 在 Amazon Linux 2 环境构建
- 使用 Docker 镜像构建

**Q: 部署包过大(>50MB)**
- 使用 Lambda Layers
- 移除未使用的依赖
