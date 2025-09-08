from typing import Dict, Any, Optional
from abc import abstractmethod
from .base import BaseAgent
from .reader import CodeComponentType

class Writer(BaseAgent):
    def __init__(self, config_path: Optional[str] = None):
        super().__init__("Writer", config_path=config_path)

        self.base_prompt = """You are a Writer agent responsible for generating high-quality 
        docstrings that are both complete and helpful. Accessible context is provided to you for 
        generating the docstring.
        
        General Guidelines:
        1. Make docstrings actionable and specific:
           - Focus on practical usage
           - Highlight important considerations
           - Include warnings or gotchas
        
        2. Use clear, concise language:
           - Avoid jargon unless necessary
           - Use active voice
           - Be direct and specific
        
        3. Type Information:
           - Include precise type hints
           - Note any type constraints
           - Document generic type parameters
        
        4. Context and Integration:
           - Explain component relationships
           - Note any dependencies
           - Describe side effects
        
        5. Follow Google docstring format:
           - Use consistent indentation
           - Maintain clear section separation
           - Keep related information grouped"""

        self.add_to_memory("system", self.base_prompt)

        self.class_prompt = """You are documenting a CLASS. Focus on describing the object it represents 
        and its role in the system.

        Required sections:
        1. Summary: 
           - One-line description focusing on WHAT the class represents
           - Avoid repeating the class name or obvious terms
           - Focus on the core purpose or responsibility
        
        2. Description: 
           - WHY: Explain the motivation and purpose behind this class
           - WHEN: Describe scenarios or conditions where this class should be used
           - WHERE: Explain how it fits into the larger system architecture
           - HOW: Provide a high-level overview of how it achieves its purpose
        
        3. Example: 
           - Show a practical, real-world usage scenario
           - Include initialization and common method calls
           - Demonstrate typical workflow

        Conditional sections:
        1. Parameters (if class's __init__ has parameters):
           - Focus on explaining the significance of each parameter
           - Include valid value ranges or constraints
           - Explain parameter relationships if they exist
        
        2. Attributes:
           - Explain the purpose and significance of each attribute
           - Include type information and valid values
           - Note any dependencies between attributes"""

        self.function_prompt = """You are documenting a FUNCTION or METHOD. Focus on describing 
        the action it performs and its effects.

        Required sections:
        1. Summary:
           - One-line description focusing on WHAT the function does
           - Avoid repeating the function name
           - Emphasize the outcome or effect
        
        2. Description:
           - WHY: Explain the purpose and use cases
           - WHEN: Describe when to use this function
           - WHERE: Explain how it fits into the workflow
           - HOW: Provide high-level implementation approach

        Conditional sections:
        1. Args (if present):
           - Explain the significance of each parameter
           - Include valid value ranges or constraints
           - Note any parameter interdependencies
        
        2. Returns:
           - Explain what the return value represents
           - Include possible return values or ranges
           - Note any conditions affecting the return value
        
        3. Raises:
           - List specific conditions triggering each exception
           - Explain how to prevent or handle exceptions
        
        4. Examples (if public and not abstract):
           - Show practical usage scenarios
           - Include common parameter combinations
           - Demonstrate error handling if relevant"""

    def is_class_component(code: str) -> bool:
        return "class " in code.split('\n')[0]

    def get_custom_prompt(self, code: str) -> str:
        is_class = self.is_class_component(code)
        specific_prompt = self.class_prompt if is_class else self.function_prompt
        return specific_prompt

    def extract_docstring(self, response: str) -> str:
        start_tag = "<DOCSTRING>"
        end_tag = "</DOCSTRING>"
        
        try:
            start_idx = response.index(start_tag) + len(start_tag)
            end_idx = response.index(end_tag)
            return response[start_idx:end_idx].strip()
        except ValueError:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("\033[93mError parsing, no DOCSTRING XML tags found in response, directly return the response as docstring %s\033[0m")
            return response

    def process(self, focal_component: str, context: Dict[str, Any]) -> str:
        task_description = f"""
        Available context:
        {context}

        {self.get_custom_prompt(focal_component)}

        Now, generate a high-quality docstring for the following Code Component based on the Available context:
        
        <FOCAL_CODE_COMPONENT>
        {focal_component}
        </FOCAL_CODE_COMPONENT>

        Keep in mind:
        1. Generate docstring between XML tag: <DOCSTRING> and </DOCSTRING>
        2. First analysis the code component and then generate the docstring at the end based on the context.
        3. Do not add triple quotes (\"\"\") to your generated docstring.
        4. Always double check if the generated docstring is within the XML tags: <DOCSTRING> and </DOCSTRING>. This is critical for parsing the docstring.
        """
        self.add_to_memory("user", task_description)
        
        full_response = self.generate_response()
        
        return self.extract_docstring(full_response)