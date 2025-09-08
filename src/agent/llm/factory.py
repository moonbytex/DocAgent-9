from typing import Dict, Any, Optional
from pathlib import Path
import yaml

from .base import BaseLLM
from .aliyun_llm import AliyunLLM

class LLMFactory:
    @staticmethod
    def create_llm(config: Dict[str, Any]) -> BaseLLM:
        llm_type = config["type"].lower()
        model = config["model"]
        rate_limits = config["rate_limits"]

        if llm_type == "aliyun":
            return AliyunLLM(
                api_key=config["api_key"],
                model=model,
                rate_limits=rate_limits
            )
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")

    @staticmethod
    def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent.parent / "config" / "agent_config.yaml")
        
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # 读取agent_config.yaml文件
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config 