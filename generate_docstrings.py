import os
import sys
import time
import ast
import json
import argparse
import logging
import random
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
import tiktoken

from src.agent.orchestrator import Orchestrator
from src.dependency_analyzer import (
    CodeComponent,
    DependencyParser,
    dependency_first_dfs,
    build_graph_from_components
)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("docstring_generator")

def main():
    parser = argparse.ArgumentParser(description='Generate docstrings for Python components in dependency order.')
    parser.add_argument('--repo-path', type=str, default='data/raw_test_repo', help='Path to the repository')
    parser.add_argument('--config-path', type=str, default='config/agent_config.yaml', help='Path to the configuration file')
    parser.add_argument('--test-mode', type=str, default='none', help='reader_searcher: no LLM calls, context_print, none: normal operation')
    parser.add_argument('--order-mode', type=str, choices=['topo', 'random_node', 'random_file'], default='topo', help='')
    parser.add_argument('--enable-web', action='store_true', help='Enable integration with the web interface')
    parser.add_argument('--overwrite-docstrings', action='store_true', help='Overwrite existing docstrings instead of skipping them')

    # 读取参数
    args = parser.parse_args()
    repo_path = args.repo_path
    config_path = args.config_path
    test_mode = args.test_mode
    order_mode = args.order_mode
    overwrite_docstrings = args.overwrite_docstrings

    # 创建依赖图文件夹
    output_dir = os.path.join("output", "dependency_graphs")
    os.makedirs(output_dir, exist_ok=True)

    # 处理仓库名称并构建依赖图文件名称
    repo_name = os.path.basename(os.path.normpath(repo_path))
    sanitized_repo_name = ''.join(c if c.isalnum() else '_' for c in repo_name)
    dependency_graph_path = os.path.join(output_dir, f'{sanitized_repo_name}_denpendency_graph.json')

    orchestrator = None
    if test_mode != 'placeholder':
        logger.info(f"Initializing orchestrator with config: {config_path}")
        orchestrator_test_mode = test_mode if test_mode != 'none' else None
        orchestrator = Orchestrator(repo_path=repo_path, config_path=config_path, test_mode=orchestrator_test_mode)
        
        # 原始代码中使用config.yaml中的overwrite_docstrings作为最终设置，这里直接使用命令行参数
        if overwrite_docstrings:
            logger.info(f"overwrite_docstrings: {overwrite_docstrings}")
    else:
        logger.info("Running in PLACEHOLDER TEST MODE with placeholder docstrings (no LLM calls)")
    
    # 基于仓库建立依赖图
    logger.info(f"Parsing repository: {repo_path}")
    parser = DependencyParser(repo_path)
    components = parser.parse_repository()
    
    # 保存依赖图
    parser.save_dependency_graph(dependency_graph_path)
    logger.info(f"Dependency graph saved to: {dependency_graph_path}")

    # dependency_graph: id -> list[id]
    graph = build_graph_from_components(components)
    dependency_graph = {}
    for component_id, deps in graph.items():
        dependency_graph[component_id] = list(deps)

    # 深度优先遍历
    logger.info("Performing DFS traversal on the dependency graph (starting from nodes with no dependencies)")
    sorted_components = dependency_first_dfs(graph)
    logger.info(f"Sorted {len(sorted_components)} components for processing")

    # todo

if __name__ == "__main__":
    main()