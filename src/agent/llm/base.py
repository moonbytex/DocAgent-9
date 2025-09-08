from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLM(ABC):
    @abstractmethod
    def generate(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7, 
        max_output_tokens: Optional[int] = None
    ) -> str:
        pass

    @abstractmethod
    def format_message(self, role: str, content: str) -> Dict[str, str]:
        pass