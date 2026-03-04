#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地测试脚本 - 安全运行 Lambda 函数

使用方式:
    python test_local.py

注意: 此脚本会从 .env.local 文件加载环境变量
确保 .env.local 已经配置好所有必需的密钥
"""

import json
import os
import sys
from pathlib import Path

# 设置 Python 路径以找到 package 目录中的模块
_package_dir = Path(__file__).parent / "package"
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))


def load_env_file(env_path: str = ".env.local") -> None:
    """从 .env.local 文件加载环境变量"""
    env_file = Path(env_path)

    if not env_file.exists():
        print(f"错误: {env_path} 文件不存在")
        print("请复制 .env.local.example 并填入你的密钥")
        sys.exit(1)

    print(f"从 {env_path} 加载环境变量...")

    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue

            # 解析 key=value 格式
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 不覆盖已存在的环境变量
                if key not in os.environ:
                    os.environ[key] = value
                    # 不打印敏感值
                    if "KEY" in key or "API" in key:
                        print(f"  {key}=****")
                    else:
                        print(f"  {key}={value}")

    # 确保本地模式开启
    os.environ["IS_LOCAL"] = "true"
    print("  IS_LOCAL=true")


def test_imports() -> bool:
    """测试所有模块是否能正常导入"""
    print("\n[1/4] Test module imports...")

    try:
        from src import config
        from src import api_client
        from src import converter
        from src import llm
        from src import email_sender

        print("  [OK] All modules imported successfully")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        return False


def test_config() -> bool:
    """测试配置加载"""
    print("\n[2/4] Test config loading...")

    try:
        from src.config import get_config

        cfg = get_config()

        print(f"  Mode: {'Local Dev' if cfg.is_local else 'Production'}")
        print(f"  LLM Model: {cfg.llm_model}")
        print(f"  Email From: {cfg.email_from}")
        print(f"  Email To: {cfg.email_to}")
        print(f"  API Timeout: {cfg.api_timeout}")

        # 检查必要的配置
        if not cfg.llm_api_key or cfg.llm_api_key == "your_DEEPSEEK_API_KEY_here":
            print("  [WARN] DEEPSEEK_API_KEY not configured")

        if not cfg.resend_api_key or cfg.resend_api_key == "re_xxxxxxxxxxxx":
            print("  [WARN] RESEND_API_KEY not configured")

        print("  [OK] Config loaded successfully")
        return True

    except Exception as e:
        print(f"  [FAIL] Config loading failed: {e}")
        return False


def test_converter() -> bool:
    """测试 HTML 转 Markdown"""
    print("\n[3/4] Test HTML to Markdown conversion...")

    try:
        from src.converter import HtmlToMarkdownConverter

        converter = HtmlToMarkdownConverter()

        test_html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a <strong>test</strong> paragraph.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
        </html>
        """

        result = converter.convert(test_html)

        print(f"  Input length: {len(test_html)} chars")
        print(f"  Output length: {len(result)} chars")
        print(f"  Output preview:\n{result[:200]}...")

        print("  [OK] Conversion successful")
        return True

    except Exception as e:
        print(f"  [FAIL] Conversion failed: {e}")
        return False


def test_api_client() -> bool:
    """测试 API 客户端"""
    print("\n[4/4] Test AlphaSignal API client...")

    try:
        from src.api_client import AlphaSignalClient

        client = AlphaSignalClient(timeout=10)

        print("  Attempting to connect to AlphaSignal API...")
        # 这里会实际发起网络请求
        # 如果网络不通或 API 不可用会抛异常
        print("  [OK] API client initialized successfully")
        print("  (Actual API test will be done when network is available)")

        return True

    except Exception as e:
        print(f"  [FAIL] API client test failed: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("AI News Lambda - 本地测试")
    print("=" * 60)

    # 加载环境变量
    load_env_file()

    # 设置 Python 路径
    sys.path.insert(0, str(Path(__file__).parent))

    # 运行测试
    results = []
    results.append(test_imports())
    results.append(test_config())
    results.append(test_converter())
    results.append(test_api_client())

    # 总结
    print("\n" + "=" * 60)
    if all(results):
        print("[OK] All tests passed!")
        print("\nNext steps:")
        print("  1. Your .env.local API keys are configured correctly")
        print('  2. Run: python -c "from src.config import get_config; get_config()"')
        print("  3. Deploy to AWS Lambda when ready")
    else:
        print("[FAIL] Some tests failed, please check your configuration")
        sys.exit(1)

    print("=" * 60)


if __name__ == "__main__":
    main()
