from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import os
from pathlib import Path

from .llm.factory import LLMFactory
from .llm.base import BaseLLM

class BaseAgent(ABC):
    def __init__(self, name: str, config_path: Optional[str] = None):
        self.name = name
        self._memory: list[Dict[str, Any]] = []
        self.llm, self.llm_params = self._initialize_llm(name, config_path)

    def _initialize_llm(self, name: str, config_path: Optional[str] = None) -> tuple[BaseLLM, Dict[str, Any]]:
        if config_path is None:
            config_path = "config/agent_config.yaml"
            print(f"Using default config from {config_path}")
        
        config = LLMFactory.load_config(config_path)

        llm_config = config.get("llm", {})
        llm_type = llm_config.get("type", "aliyun")
        rate_limits = config.get("rate_limits", {}).get(llm_type, {})
        llm_config["rate_limits"] = rate_limits

        llm_params = {
            "max_output_tokens": llm_config.get("max_output_tokens", 4096),
            "temperature": llm_config.get("temperature", 0.2),
            "model": llm_config.get("model")
        }

        # 返回一个LLM
        return LLMFactory.create_llm(llm_config), llm_params

    def add_to_memory(self, role: str, content: str) -> None:
        assert content is not None and content != "", "Content cannot be empty"
        self._memory.append(self.llm.format_message(role, content))

    def refresh_memory(self, new_memory: list[Dict[str, Any]]) -> None:
        self._memory = [
            self.llm.format_message(msg["role"], msg["content"])
            for msg in new_memory
        ]

    def clear_memory(self) -> None:
        self._memory = []

    @property
    def memory(self) -> list[Dict[str, Any]]:
        return self._memory.copy()

    def generate_response(self, messages: Optional[List[Dict[str, Any]]] = None) -> str:
        return self.llm.generate(
            messages=messages if messages is not None else self._memory,
            temperature=self.llm_params["temperature"],
            max_tokens=self.llm_params["max_output_tokens"]
        )
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        # 处理输入和生成
        pass