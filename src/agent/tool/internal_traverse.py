import ast
import os
from typing import List, Optional, Dict, Any, Tuple

class ASTNodeAnalyzer:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    # 返回dependency_path对应的代码组件
    def get_component_by_path(
        self,
        ast_node: ast.AST,
        ast_tree: ast.AST,
        dependency_path: str
    ) -> Optional[str]:
        path_parts = dependency_path.split('.')
        if len(path_parts) < 2:
            return None

        # 判断是否是方法
        if len(path_parts) >= 3 and path_parts[-2] != 'self':
            last_part = path_parts[-1]
            second_last_part = path_parts[-2]
            
            # 是file.class.method 
            if last_part[0].islower() and second_last_part[0].isupper():
                return self._get_method_component(ast_node, ast_tree, dependency_path)

        # 判断是否是类
        if path_parts[-1][0].isupper():
            return self._get_class_component(ast_node, ast_tree, dependency_path)

        # 最后是函数
        return self._get_function_component(ast_node, ast_tree, dependency_path)

    # 返回方法组件的代码
    def _get_method_component(self, ast_node: ast.AST, ast_tree: ast.AST, dependency_path: str) -> Optional[str]:
        path_parts = dependency_path.split('.')
        if len(path_parts) < 3:
            return None

        method_name = path_parts[-1]
        class_name = path_parts[-2]
        file_name = path_parts[-3]
        folder_path = os.path.join(*path_parts[:-3]) if len(path_parts) > 3 else ''
        
        # self说明当前关注的代码组件是类
        if class_name == 'self':
            if isinstance(ast_node, ast.ClassDef):
                for item in ast_node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        return self._get_node_source(file_path=os.path.relpath(ast_tree.file_path, self.repo_path) if hasattr(ast_tree, 'file_path') else "", node=item)
            return None

        target_file_path = os.path.join(folder_path, file_name)
        full_file_path = os.path.join(self.repo_path, target_file_path)
        
        # 如果文件路径不存在，就检查当前文件
        if not os.path.exists(full_file_path):
            for node in ast.walk(ast_tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == method_name:
                            return self._get_node_source(file_path=os.path.relpath(ast_tree.file_path, self.repo_path) if hasattr(ast_tree, 'file_path') else "", node=item)
            return None

        # 正常读取文件中的内容
        try:
            with open(full_file_path, 'r') as f:
                file_content = f.read()
                target_ast = ast.parse(file_content)
            
            for node in ast.walk(target_ast):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == method_name:
                            return self.get_node_source(target_file_path, item)
        except Exception as e:
            return f"Error retrieving method {class_name}.{method_name}: {e}"

        return None

    # 返回函数的代码
    def _get_function_component(self, ast_node: ast.AST, ast_tree: ast.AST, dependency_path: str) -> Optional[str]:
        path_parts = dependency_path.split('.')
        function_name = path_parts[-1]
        file_name = path_parts[-2]
        folder_path = os.path.join(*path_parts[:-2] if len(path_parts) > 2 else '')

        # self说明指的是当前组件
        if function_name == 'self':
            if isinstance(ast_node, ast.FunctionDef):
                return self._get_node_source(file_path=os.path.relpath(ast_tree.file_path, self.repo_path) if hasattr(ast_tree, 'file_path') else "", node=ast_node)
            return None

        target_file_path = os.path.join(folder_path, file_name)
        full_file_path = os.path.join(self.repo_path, target_file_path)
        
        # 如果文件不存在，检查当前文件
        if not os.path.exists(full_file_path):
            for node in ast.walk(ast_tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    return self._get_node_source(file_path=os.path.relpath(ast_tree.file_path, self.repo_path) if hasattr(ast_tree, 'file_path') else "", node=node)
            return None

        try:
            with open(full_file_path, 'r') as f:
                file_content = f.read()
                target_ast = ast.parse(file_content)

            for node in ast.walk(target_ast):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    return self._get_node_source(target_file_path, node)
        except Exception as e:
            return f"Error retrieving function {function_name}: {e}"

        return None

    def _get_class_component(self, ast_node: ast.AST, ast_tree: ast.AST, dependency_path: str) -> Optional[str]:
        path_parts = dependency_path.split('.')
        class_name = path_parts[-1]
        file_name = path_parts[-2] + '.py'
        folder_path = os.path.join(*path_parts[:-2] if len(path_parts) > 2 else '')
        
        # self说明指的是自己
        if class_name == 'self':
            if isinstance(ast_node, ast.ClassDef):
                return self._get_node_source(file_path=os.path.relpath(ast_tree.file_path, self.repo_path) if hasattr(ast_tree, 'file_path') else "", node=ast_node)
            return None

        # 源代码说检查类是否被当前文件使用，应该是ast_tree？而且也不知道在返回什么
        local_class_info = self._find_class_init_in_node(ast_node, class_name)
        if local_class_info:
            return local_class_info

        target_file_path = os.path.join(folder_path, file_name)
        full_file_path = os.path.join(self.repo_path, target_file_path)
        
        if not os.path.exists(full_file_path):
            return None

        try:
            with open(full_file_path, 'r') as f:
                file_content = f.read()
                target_ast = ast.parse(file_content)

            for node in ast.walk(target_ast):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    return self._get_node_source(target_file_path, node)
        except Exception as e:
            return f"Error retrieving class {class_name}: {e}"

        return None

    def _get_node_source(self, file_path: str, node: ast.AST) -> str:
        try:
            full_path = os.path.join(self.repo_path, file_path)
            with open(full_path, 'r') as f:
                file_content = f.read()

            start_line = node.lineno
            end_line = self._get_end_line(node)
            lines = file_content.split('\n')

            # if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            #     if (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str)):
            #         pass

            end_line = min(end_line, len(lines))
            return '\n'.join(lines[start_line - 1: end_line])
        except Exception as e:
            return f"Error retrieving source for {type(node).__name__}: {e}"

    def _get_end_line(self, node: ast.AST) -> int:
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        if hasattr(node, 'body') and node.body:
            last_subnode = node.body[-1]
            return self._get_end_line(last_subnode, file_content)
        return node.lineno

    def _find_class_init_in_node(self, ast_node: ast.AST, class_name: str) -> Optional[str]:
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Call) and self._get_call_name(node) == class_name:
                return self._format_call_node(node)
        return None

    def _get_call_name(self, call_node: ast.Call) -> Optional[str]:
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return None

    def _format_call_node(self, call_node: ast.Call) -> str:
        call_name = self._get_call_name(call_node)
        return f"{call_name}(...)"