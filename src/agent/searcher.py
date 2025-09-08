from typing import Dict, List, Any, Optional
import re
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
from io import StringIO
import ast

from .base import BaseAgent
from .reader import InformationRequest
# 内部搜索和外部搜索
from .tool.internal_traverse import ASTNodeAnalyzer
from .tool.perplexity_api import PerplexityAPI

@dataclass
class ParsedInfoRequest:
    """结构化的内部请求和外部请求"""
    internal_requests: Dict[str, Any] = field(default_factory=lambda: {
        'calls': {
            'class': [],
            'function': [],
            'method': []
        },
        'call_by': False
    })
    external_requests: List[str] = field(default_factory=list)

class Searcher(BaseAgent):
    """收集内部信息和外部信息"""

    def __init__(self, repo_path: str, config_path: Optional[str] = None):
        super().__init__("Searcher", config_path=config_path)
        self.repo_path = repo_path
        self.ast_analyzer = ASTNodeAnalyzer(repo_path)

    def process(
        self,
        reader_response: str,
        ast_node: ast.AST,
        ast_tree: ast.AST,
        dependency_graph: Dict[str, List[str]],
        focal_node_dependency_path: str,
    ) -> Dict[str, Any]:
        # 解析reader的返回内容
        parsed_request = self._parse_reader_response(reader_response)

        # 使用依赖图和AST分析收集内部信息
        internal_info = self._gather_internal_info(
            ast_node,
            ast_tree,
            focal_node_dependency_path,
            dependency_graph,
            parsed_request
        )

        external_info = self._gather_external_info(parsed_request.external_requests)

        return {
            'internal': internal_info,
            'external': external_info
        }

    def _parse_reader_response(self, reader_response: str) -> ParsedInfoRequest:
        # 正则提取xml内容
        xml_match = re.search(r'<REQUEST>(.*?)</REQUEST>', reader_response, re.DOTALL)
        if not xml_match:
            return ParsedInfoRequest()
        xml_content = f'<REQUEST>{xml_match.group(1)}</REQUEST>'
        
        try:
            root = ET.fromstring(xml_content)

            # 解析内部请求
            internal = root.find('INTERNAL')
            calls = internal.find('CALLS')
            internal_requests = {
                'calls': {
                    'class': self._parse_comma_list(calls.find('CLASS').text),
                    'function': self._parse_comma_list(calls.find('FUNCTION').text),
                    'method': self._parse_comma_list(calls.find('METHOD').text)
                },
                'call_by': internal.find('CALL_BY').text.lower() == 'true'
            }

            # 解析外部请求
            external = root.find('RETRIEVAL')
            external_requests = self._parse_comma_list(external.find('QUERY').text)

            return ParsedInfoRequest(
                internal_requests=internal_requests,
                external_requests=external_requests
            )

        except (ET.ParseError, AttributeError) as e:
            print(f'Error parsing XML: {e}')
            return ParsedInfoRequest()

    # 按照,分隔成list
    def _parse_comma_list(self, text: str | None) -> List[str]:
        if not text:
            return []
        return [item.strip() for item in text.split(',') if item.strip()]

    def _gather_internal_info(
        self,
        ast_node: ast.AST,
        ast_tree: ast.AST,
        focal_dependency_path: str,
        dependency_graph: Dict[str, List[str]],
        parsed_request: ParsedInfoRequest
    ):
        result = {
            'calls': {
                'class': {},
                'function': {},
                'method': {}
            },
            'called_by': []
        }

        # 从依赖图中获得给定代码组件的依赖
        component_dependencies = dependency_graph.get(focal_dependency_path, [])

        # 处理类依赖，将请求中的类信息加入进去
        if parsed_request.internal_requests['calls']['class']:
            requested_classes = parsed_request.internal_requests['calls']['class']
            # 遍历所有依赖，判断哪个依赖是reader请求的
            for dependency_path in component_dependencies:
                path_parts = dependency_path.split('.')
                # 如果最后一部分首字母大写，说明是类
                if path_parts and path_parts[-1][0].isupper():
                    class_name = path_parts[-1]

                    for requested_class in requested_classes:
                        if (requested_class == class_name or
                            requested_class in dependency_path or
                            class_name.endswith(requested_class)):
                            
                            # 获得类初始化代码
                            class_code = self.ast_analyzer.get_component_by_path(
                                ast_node,
                                ast_tree,
                                dependency_path
                            )

                            if class_code:
                                result['calls']['class'][requested_class] = class_code
                                break

        # 处理函数依赖
        if parsed_request.internal_requests['call']['function']:
            requested_functions = parsed_request.internal_requests['call']['function']
            for dependency_path in component_dependencies:
                path_parts = dependency_path.split('.')
                # 如果首字母小写，可能是函数或方法
                if path_parts and path_parts[-1][0].islower():
                    # 如果倒数第二个首字母大写，则是类中的方法，跳过
                    if len(path_parts) >= 2 and path_parts[-2][0].isupper():
                        continue

                    function_name = path_parts[-1]

                    for requested_function in requested_functions:
                        if (requested_function == function_name or
                            requested_function in dependency_path or
                            function_name.endswith(requested_function)):
                            
                            # 获得函数代码
                            function_code = self.ast_analyzer.get_component_by_path(
                                ast_node,
                                ast_tree,
                                dependency_path
                            )

                            if function_code:
                                result['calls']['function'][requested_function] = function_code
                                break

        # 处理方法依赖
        if parsed_request.internal_requests['calls']['method']:
            requested_methods = parsed_request.internal_requests['calls']['method']
            for dependency_path in component_dependencies:
                path_parts = dependency_path.split('.')
                if len(path_parts) >= 2 and path_parts[-1][0].islower() and path_parts[-2][0].isupper():
                    method_name = path_parts[-1]
                    class_name = path_parts[-2]
                    full_method_name = f"{class_name}.{method_name}"
                    
                    for requested_method in requested_methods:
                        if (requested_method == full_method_name or
                            requested_method == method_name or
                            requested_method in dependency_path or
                            method_name.endswith(requested_method)):
                            
                            method_code = self.ast_analyzer.get_component_by_path(
                                ast_node,
                                ast_tree,
                                dependency_path
                            )

                            if method_code:
                                result['calls']['method'][requested_method] = method_code
                                break
            
    def _gather_external_info(self, queries: List[str]) -> Dict[str, str]:
        if not queries:
            return {}

        try:
            perplexity = PerplexityAPI()
            responses = perplexity.batch_query(
                questions=queries,
                system_prompt="You are a helpful assistant providing concise and accurate information about programming concepts and code. Focus on technical accuracy and clarity.",
                temperature=0.1
            )

            result = {}
            for query, response in zip(queries, responses):
                if response is not None:
                    result[query] = response.content
                else:
                    result[query] = "Error: Failed to get response from Perplexity API"

        except Exception as e:
            print(f"Error using Perplexity API: {str(e)}")
            return {query: f"Error: {str(e)}" for query in queries}