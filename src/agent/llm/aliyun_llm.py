from typing import List, Dict, Any, Optional
from transformers import AutoTokenizer
import requests

from .base import BaseLLM
from .rate_limiter import RateLimiter

class AliyunLLM(BaseLLM):
    def __init__(
        self,
        api_key: str,
        model: str,
        rate_limits: Optional[Dict[str, Any]] = None
    ):
        self.aliyun_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.api_key = api_key
        self.model = model

        self.payload = {
            "model": model,
            "messages": None,
            "stream": False,
            "max_tokens": None,
            "temperature": None,
            "top_p": 0.95,
            "top_k": 50,
            "frequency_penalty": 0,
        }

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 定义tokenizer, 计算token数量
        self.tokenizer = AutoTokenizer.from_pretrained("/data8/huangjinpeng/CodeModel/Qwen2.5-Coder-7B-Instruct")
        
        default_limits = {
            "requests_per_minute": 10,
            "input_tokens_per_minute": 2000,
            "output_tokens_per_minute": 800,
            "input_token_price_per_million": 0,
            "output_token_price_per_million": 0
        }
        limits = rate_limits or default_limits

        self.rate_limiter = RateLimiter(
            provider="aliyun",
            requests_per_minute=limits.get("requests_per_minute", default_limits["requests_per_minute"]),
            input_tokens_per_minute=limits.get("input_tokens_per_minute", default_limits["input_tokens_per_minute"]),
            output_tokens_per_minute=limits.get("output_tokens_per_minute", default_limits["output_tokens_per_minute"]),
            input_token_price_per_million=limits.get("input_token_price_per_million", default_limits["input_token_price_per_million"]),
            output_token_price_per_million=limits.get("output_token_price_per_million", default_limits["output_token_price_per_million"])
        )

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            import logging
            logging.warning(f"Failed to count tokens with tokenizer: {e}")
            return len(text.split()) * 1.3
    
    def _count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        if not messages:
            return 0

        total_tokens = 0
        
        for message in messages:
            if "content" in message and message["content"]:
                total_tokens += self._count_tokens(message["content"])
        
        total_tokens += 4 * len(messages)

        total_tokens += 3

        return total_tokens

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int]
    ) -> str:
        # 计算输入tokens数量
        input_tokens = self._count_messages_tokens(messages)

        # 检查是否需要等待
        self.rate_limiter.wait_if_needed(input_tokens, max_tokens)

        # 填写参数
        self.payload["messages"] = messages
        self.payload["temperature"] = temperature
        self.payload["max_tokens"] = max_tokens
        completion = requests.request("POST", self.aliyun_url, json=self.payload, headers=self.headers).json()
        
        result_text = completion["choices"][0]["message"]["content"]
        input_tokens = completion["usage"]["prompt_tokens"]
        output_tokens = completion["usage"]["completion_tokens"]

        # 记录这次输入输出
        self.rate_limiter.record_request(input_tokens, output_tokens)

        return result_text

    def format_message(self, role: str, content: str) -> Dict[str, str]:
        return {"role": role, "content": content}