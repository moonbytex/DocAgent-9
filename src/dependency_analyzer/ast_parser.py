import ast
import os
import json
import logging
import builtins
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

# 其中一些类型和模块需要从依赖中排除
BUILTIN_TYPES = {name for name in dir(builtins)}
STANDARD_MODULES = {
    'abc', 'argparse', 'array', 'asyncio', 'base64', 'collections', 'copy', 
    'csv', 'datetime', 'enum', 'functools', 'glob', 'io', 'itertools', 
    'json', 'logging', 'math', 'os', 'pathlib', 'random', 're', 'shutil', 
    'string', 'sys', 'time', 'typing', 'uuid', 'warnings', 'xml'
}
EXCLUDED_NAMES = {'self', 'cls'}

@dataclass
class CodeComponent:
    id: str # module_path.ClassName.method_name
    node: ast.AST
    component_type: str # class function method
    file_path: str
    relative_path: str # 相对repo
    depends_on: Set[str] = field(default_factory=set)
    source_code: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    has_docstring: bool = False
    docstring: str = ""

    # 没有node和source_code
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'component_type': self.component_type,
            'file_path': self.file_path,
            'relative_path': self.relative_path,
            'depends_on': list(self.depends_on),
            'start_line': self.start_line,
            'end_line': self.end_line,
            'has_docstring': self.has_docstring,
            'docstring': self.docstring
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'CodeComponent':
        component = CodeComponent(
            id=data['id'],
            node=None,  # AST node is not serialized
            component_type=data['component_type'],
            file_path=data['file_path'],
            relative_path=data['relative_path'],
            depends_on=set(data.get('depends_on', [])),
            start_line=data.get('start_line', 0),
            end_line=data.get('end_line', 0),
            has_docstring=data.get('has_docstring', False),
            docstring=data.get('docstring', "")
        )
        return component

def add_parent_to_nodes(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

class ImportCollector(ast.NodeVisitor):
    def __init__(self):
        self.imports = set()
        self.from_imports = {}

    def visit_Import(self, node: ast.Import):
        # 处理import ...
        for name in node.names:
            self.imports.add(name.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # 处理from ... import ...
        if node.module is not None:
            module = node.module
            if module not in self.from_imports:
                self.from_imports[module] = []

            for name in node.names:
                if name.name != '*':
                    self.from_imports[module].append(name.name)
        
        self.generic_visit(node)

class DependencyCollector(ast.NodeVisitor):
    def __init__(self, imports, from_imports, current_module, repo_modules):
        self.imports = imports
        self.from_imports = from_imports
        self.current_module = current_module
        self.repo_modules = repo_modules
        self.dependencies = set()
        self._current_class = None
        self.local_variables = set()

    def _add_dependency(self, name):
        # 只检查了from ... imports ... 的情况
        if name in BUILTIN_TYPES:
            return

        if name in EXCLUDED_NAMES:
            return 

        if name in self.local_variables:
            return 
        
        for module, imported_names in self.from_imports.items():
            if module in STANDARD_MODULES:
                continue

            if name in imported_names and module in self.repo_modules:
                self.dependencies.add(f"{module}.{name}")
                return 

        # 如果不在导入中，就在当前文件中
        local_component_id = f"{self.current_module}.{name}"
        self.dependencies.add(local_component_id)

    def _process_attribute(self, node: ast.Attribute):
        parts = []
        current = node
        
        # 遍历attibute链 例如module.submodule.Class.method
        while isinstance(current, ast.Attribute):
            parts.insert(0, current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.insert(0, current.id)

            # 跳过本地变量
            if parts[0] in self.local_variables:
                return
            
            # 跳过self cls
            if parts[0] in EXCLUDED_NAMES:
                return

            if parts[0] in self.imports:
                module_path = parts[0]
                # 跳过标准库
                if module_path in STANDARD_MODULES:
                    return

                if module_path in self.repo_modules:
                    if len(parts) > 1:
                        self.dependencies.add(f"{module_path}.{parts[1]}")
        
            elif parts[0] in self.from_imports.keys():
                if parts[0] in STANDARD_MODULES:
                    return

                if len(parts) > 1 and parts[1] in self.from_imports[parts[0]]:
                    self.dependencies.add(f"{parts[0]}.{parts[1]}")

    def visit_ClassDef(self, node: ast.ClassDef):
        old_class = self._current_class
        self._current_class = node.name

        # 检查当前类继承的基类
        for base in node.bases:
            if isinstance(base, ast.Name):
                self._add_dependency(base.id)
            elif isinstance(base, ast.Attribute):
                self._process_attribute(base)

        self.generic_visit(node)
        self._current_class = old_class

    def visit_Assign(self, node: ast.Assign):
        # 跟踪本地变量
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.local_variables.add(target.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            # 直接函数调用
            self._add_dependency(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # module.function call
            self._process_attribute(node.func)
        
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        # 表示读取变量
        if isinstance(node.ctx, ast.Load):
            self._add_dependency(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        self._process_attribute(node)
        self.generic_visit(node)

class DependencyParser:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.components: Dict[str, CodeComponent] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.modules: Set[str] = set()

    def _file_to_module_path(self, file_path: str) -> str:
        path = file_path[:-3] if file_path.endswith(".py") else file_path
        return path.replace(os.path.sep, ".")

    def _get_docstring(self, source: str, node: ast.AST) -> str:
        try:
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                for item in node.body:
                    if isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant):
                        if isinstance(item.value.value, str):
                            return item.value.value
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant):
                        if isinstance(item.value.value, str):
                            return item.value.value
            return ""
        except Exception as e:
            logger.warning(f"Error getting docstring: {e}")
            return ""

    def _get_source_segment(self, source: str, node: ast.AST) -> str:
        # 从source中提取出node对应的代码
        try:
            if hasattr(ast, "get_source_segment"):
                segment = ast.get_source_segment(source, node)
                if segment is not None:
                    return segment
            
            # Fallback to manual extraction
            lines = source.split("\n")
            start_line = node.lineno - 1
            end_line = getattr(node, "end_lineno", node.lineno) - 1
            return "\n".join(lines[start_line:end_line + 1])
        
        except Exception as e:
            logger.warning(f"Error getting source segment: {e}")
            return ""

    # 收集指定文件的组件
    def _collect_components(self, tree: ast.AST, file_path: str, relative_path: str, module_path: str, source: str):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_id = f"{module_path}.{node.name}"
                
                # 检查是否有文档
                has_docstring = (
                    len(node.body) > 0
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )

                # 提取文档
                docstring = self._get_docstring(source, node) if has_docstring else ""

                component = CodeComponent(
                    id=class_id,
                    node=node,
                    component_type="class",
                    file_path=file_path,
                    relative_path=relative_path,
                    source_code=self._get_source_segment(source, node),
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    has_docstring=has_docstring,
                    docstring=docstring
                )

                self.components[class_id] = component

                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_id = f"{class_id}.{item.name}"

                        method_has_docstring = (
                            len(node.body) > 0
                            and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)
                        )

                        method_docstring = self._get_docstring(source, item) if method_has_docstring else ""

                        method_component = CodeComponent(
                            id=method_id,
                            node=item,
                            component_type="method",
                            file_path=file_path,
                            relative_path=relative_path,
                            source_code=self._get_source_segment(source, item),
                            start_line=item.lineno,
                            end_line=getattr(item, "end_lineno", item.lineno),
                            has_docstring=method_has_docstring,
                            docstring=method_docstring,
                        )

                        self.components[method_id] = method_component
            
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 只收集最上层的函数
                if hasattr(node, 'parent') and isinstance(node.parent, ast.Module):
                    func_id = f"{module_path}.{node.name}"

                    has_docstring = (
                        len(node.body) > 0
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    )

                    docstring = self._get_string(source, node) if has_docstring else ""

                    component = CodeComponent(
                        id=func_id,
                        node=node,
                        component_type="function",
                        file_path=file_path,
                        relative_path=relative_path,
                        source_code=self._get_source_segment(source, node),
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        has_docstring=has_docstring,
                        docstring=docstring
                    )
                    
                    self.components[func_id] = component

    # 为收集指定文件组件做准备
    def _parse_file(self, file_path: str, relative_path: str, module_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

            # 给ast树的每一个节点添加父亲节点
            add_parent_to_nodes(tree)

            # 收集import ... 和from ... import ... 导入的包 没用到
            import_collector = ImportCollector()
            import_collector.visit(tree)

            self._collect_components(tree, file_path, relative_path, module_path, source)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Error parsing {file_path}: {e}")

    # 收集组件依赖
    def _resolve_dependencies(self):
        for component_id, component in self.components.items():
            file_path = component.file_path

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()

                tree = ast.parse(source)

                add_parent_to_nodes(tree)

                import_collector = ImportCollector()
                import_collector.visit(tree)

                comonent_node = None
                module_path = self._file_to_module_path(component.relative_path)

                # 其实可以直接使用component中存的node
                if component.component_type == "function":
                    for node in ast.iter_child_nodes(tree):
                        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and node.name == component.id.split('.')[-1]):
                            component_node = node

                elif component.component_type == 'class':
                    for node in ast.iter_child_nodes(tree):
                        if isinstance(node, ast.ClassDef) and node.name == component.id.split('.')[-1]:
                            component_node = node
                            break

                elif component.component_type == 'method':
                    class_name, method_name = component.id.split('.')[-2:]
                    class_node = None
                    
                    for node in ast.iter_child_nodes(tree):
                        if isinstance(node, ast.ClassDef) and node.name == class_name:
                            for item in node.body:
                                if (isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))\
                                    and item.name == method_name):
                                    component_node = item
                                    break

                                break
                
                # 收集这个组件的依赖
                if component_node:
                    dependency_collector = DependencyCollector(
                        import_collector.imports,
                        import_collector.from_imports,
                        module_path,
                        self.modules
                    )

                    if isinstance(component_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for arg in component_node.args.args:
                            dependency_collector.local_variables.add(arg.arg)

                    dependency_collector.visit(component_node)
                    
                    # 在这里给组件添加依赖
                    component.depends_on.update(dependency_collector.dependencies)

                    component.depends_on = {
                        dep for dep in component.depends_on
                        if dep in self.components or dep.split('.', 1)[0] in self.modules
                    }

            except (SyntaxError, UnicodeDecodeError) as e:
                logger.warning(f"Error analyzing dependencies in {file_path}: {e}")

    # 类的依赖添加自己的方法除了__init__
    def _add_class_method_dependencies(self):
        class_methods = {}

        for component_id, component in self.components.items():
            if component.component_type == 'method':
                parts = component_id.split(".")
                if len(parts) >= 2:
                    method_name = parts[-1]
                    class_id = ".".join(parts[:-1])
                    
                    if class_id not in class_methods:
                        class_methods[class_id] = []

                    if method_name != "__init__":
                        class_methods[class_id].append(component_id)

        for class_id, method_ids in class_methods.items():
            if class_id in self.components:
                class_component = self.components[class_id]
                for method_id in method_ids:
                    class_component.depends_on.add(method_id)

    # 收集这个仓库所有的组件class method function以及它们的信息
    def parse_repository(self):
        logger.info(f"Parsing repository at {self.repo_path}")

        # 第一步，收集所有模块和代码组件
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if not file.endswith(".py"):
                    continue 

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.repo_path)

                # 将文件路径转换成module path
                module_path = self._file_to_module_path(relative_path)
                self.modules.add(module_path)
                
                self._parse_file(file_path, relative_path, module_path)

        # 第二步
        self._resolve_dependencies()
        
        # 第三步
        self._add_class_method_dependencies()

        logger.info(f"Found {len(self.components)} code components")
        return self.components        
    
    # 保存依赖图
    def save_dependency_graph(self, output_path: str):
        serializable_components = {
            comp_id: component.to_dict()
            for comp_id, component in self.components.items()
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(serializable_components, f, indent=2)

        logger.info(f"Saved dependency graph to {output_path}")

    # 加载依赖图
    def load_dependency_graph(self, input_path: str):
        with open(input_path, "r", encoding="utf-8") as f:
            serialized_components = json.load(f)
        
        self.components = {
            comp_id: CodeComponent.from_dict(comp_data)
            for comp_id, comp_data in serialized_components.items()
        }
        
        logger.info(f"Loaded {len(self.components)} components from {input_path}")
        return self.components 