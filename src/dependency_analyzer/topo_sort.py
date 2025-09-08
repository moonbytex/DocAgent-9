import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

def build_graph_from_components(components: Dict[str, Any]) -> Dict[str, Set[str]]:
    # 实际就是把字典类型的value换成id集合了
    graph = {}

    for comp_id, component in components.items():
        if comp_id not in graph:
            graph[comp_id] = set()

        for dep_id in component.depends_on:
            if dep_id in components:
                graph[comp_id].add(dep_id)

    return graph

def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    # Implementation of Tarjan's algorithm
    index_counter = [0]
    index = {}
    lowlink = {}
    onstack = set()
    stack = []
    result = []
    
    def strongconnect(node):
        index[node] = index_counter[0]
        lowlink[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        onstack.add(node)
        
        for successor in graph.get(node, set()):
            if successor not in index:
                strongconnect(successor)
                lowlink[node] = min(lowlink[node], lowlink[successor])
            elif successor in onstack:
                lowlink[node] = min(lowlink[node], index[successor])
        
        if lowlink[node] == index[node]:
            scc = []
            while True:
                successor = stack.pop()
                onstack.remove(successor)
                scc.append(successor)
                if successor == node:
                    break
            
            if len(scc) > 1:
                result.append(scc)
    
    for node in graph:
        if node not in index:
            strongconnect(node)
    
    return result

# 破环的方法就是遇到的第一条边
def resolve_cycles(graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    cycles = detect_cycles(graph)

    if not cycles:
        logger.info("No cycles detected in the dependency graph")
        return graph

    logger.info(f"Detected {len(cycles)} cycles in the dependency graph")

    new_graph = {node: deps.copy() for node, deps in graph.items()}

    # 处理每个环
    for i, cycle in enumerate(cycles):
        logger.info(f"Cycle {i+1}: {' -> '.join(cycle)}")

        for j in range(len(cycle) - 1):
            current = cycle[j]
            next_node = cycle[j + 1]
            
            if next_node in new_graph[current]:
                logger.info(f"Breaking cycle by removing dependency: {current} -> {next_node}")
                new_graph[current].remove(next_node)
                break

    return new_graph

# 奇怪，输入的应该是Dict[str, List[str]]
# 也是一种拓扑排序
def dependency_first_dfs(graph: Dict[str, Set[str]]) -> List[str]:
    # 解决环的问题
    acyclic_graph = resolve_cycles(graph)

    root_nodes = []
    has_incoming_edge = {node: False for node in acyclic_graph}
    
    for node, deps in acyclic_graph.items():
        for dep in deps:
            has_incoming_edge[dep] = True
    
    for node in acyclic_graph:
        if not has_incoming_edge.get(node, False):
            root_nodes.append(node)

    if not root_nodes:
        logger.warning("No root nodes found in the graph, using arbitrary starting point")
        root_nodes = list(acyclic_graph.keys())[:1]

    visited = set()
    result = []

    # 深度优先搜索
    def dfs(node):
        if node in visited:
            return
        visited.add(node)

        for dep in sorted(acyclic_graph.get(node, set())):
            dfs(dep)
        
        result.append(node)

    for root in sorted(root_nodes):
        dfs(root)

    if len(result) != len(acyclic_graph):
        for node in sorted(acyclic_graph.keys()):
            if node not in visited:
                dfs(node)

    return result