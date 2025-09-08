from typing import Optional, List
from .base import BaseAgent

class Verifier(BaseAgent):
    def __init__(self, config_path: Optional[str] = None):
        super().__init__("Verifier", config_path=config_path)
        self.system_prompt = """You are a Verifier agent responsible for ensuring the quality of generated docstrings. 
        Your role is to evaluate docstrings from the perspective of a first-time user encountering the code component.
        
        Analysis Process:
        1. First read the code component as if you're seeing it for the first time
        2. Read the docstring and analyze how well it helps you understand the code
        3. Evaluate if the docstring provides the right level of abstraction and information
        
        Verification Criteria:
        1. Information Value:
           - Identify parts that merely repeat the code without adding value
           - Flag docstrings that state the obvious without providing insights
           - Check if explanations actually help understand the purpose and usage
        
        2. Appropriate Detail Level:
           - Flag overly detailed technical explanations of implementation
           - Ensure focus is on usage and purpose, not line-by-line explanation
           - Check if internal implementation details are unnecessarily exposed
        
        3. Completeness Check:
           - Verify all required sections are present (summary, args, returns, etc.)
           - Check if each section provides meaningful information
           - Ensure critical usage information is not missing
        
        Output Format:
        Your analysis must include:
        1. <NEED_REVISION>true/false</NEED_REVISION>
           - Indicates if docstring needs improvement
        
        2. If revision needed:
           <MORE_CONTEXT>true/false</MORE_CONTEXT>
           - Indicates if additional context is required for improvement
           - Keep in mind that collecting context is very expensive and may fail, so only use it when absolutely necessary
        
        3. Based on MORE_CONTEXT, provide suggestions at the end of your response:
           If true:
           <SUGGESTION_CONTEXT>explain why and what specific context is needed</SUGGESTION_CONTEXT>
           
           If false:
           <SUGGESTION>specific improvement suggestions</SUGGESTION>
        
        Do not generate other things after </SUGGESTION> or </SUGGESTION_CONTEXT>.
        """
        self.add_to_memory("system", self.system_prompt)

    def process(self, focal_component: str, docstring: str, context: str = "") -> str:
        task_description = f"""
        Context Used:
        {context if context else 'No context was used.'}

        Verify the quality of the following docstring for the following Code Component:
        
        Code Component:
        {focal_component}
        
        Generated Docstring:
        {docstring}

        """
        self.add_to_memory("user", task_description)
        
        full_response = self.generate_response()
        return full_response