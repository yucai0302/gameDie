"""LLM Agent 基础设施：OpenAI 兼容客户端 + Agent 基类。

使用标准库 urllib 调用 OpenAI 兼容 ``/chat/completions`` 接口，
零额外依赖，后端与桌面 Agent 均可直接使用。

兼容提供商（通过 base_url 区分）：
- OpenAI:    https://api.openai.com/v1
- 豆包/火山:  https://ark.cn-beijing.volces.com/api/v3
- DeepSeek:   https://api.deepseek.com/v1
- 本地模型:   http://localhost:11434/v1
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# 留空时使用的官方默认端点
DEFAULT_BASE_URL = "https://api.openai.com/v1"


class LLMClient:
    """OpenAI 兼容 Chat Completions 客户端。"""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout: float = 30.0,
    ):
        self.api_key = (api_key or "").strip()
        self.model = (model or "").strip()
        self.base_url = _normalize_base_url(base_url)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.timeout = float(timeout)

    @property
    def configured(self) -> bool:
        """是否已填写足够调用的必填项。"""
        return bool(self.api_key) and bool(self.model)

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """调用 chat/completions，返回助手消息文本。失败抛异常。"""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8")
        obj = json.loads(body)
        return obj["choices"][0]["message"]["content"]

    def test_connection(self) -> Tuple[bool, str]:
        """发送一条最小消息验证连通性，返回 (ok, message)。"""
        if not self.configured:
            return False, "缺少 API Key 或模型名称"
        try:
            reply = self.chat([{"role": "user", "content": "ping"}])
            # 截断过长的回显
            snippet = reply.strip().replace("\n", " ")
            if len(snippet) > 80:
                snippet = snippet[:80] + "..."
            return True, f"连接成功：{snippet}"
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")[:120]
            return False, f"HTTP {e.code}：{detail or e.reason}"
        except urllib.error.URLError as e:
            return False, f"网络错误：{e.reason}"
        except Exception as e:  # noqa: BLE001
            return False, f"连接失败：{type(e).__name__}: {e}"


class BaseAgent:
    """Agent 基类。子类实现 invoke(context) -> str。"""

    agent_id: str = ""
    name: str = ""
    description: str = ""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def invoke(self, context: Dict[str, Any]) -> str:
        """根据上下文生成文本。子类必须实现。"""
        raise NotImplementedError


def _normalize_base_url(base_url: str) -> str:
    """规整用户填写的 base_url。

    - 留空 → OpenAI 官方默认
    - 已含版本号（/v1、/v3 等）→ 原样保留
    - 仅填到域名 → 自动补 /v1
    """
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return DEFAULT_BASE_URL
    # 已包含 /v数字 结尾（如 /v1、/api/v3），不再补
    if re.search(r"/v\d+$", base) or base.endswith("/chat/completions"):
        return base
    return f"{base}/v1"
