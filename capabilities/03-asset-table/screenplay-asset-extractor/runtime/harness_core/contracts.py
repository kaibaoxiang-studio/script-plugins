from __future__ import annotations

from jsonschema import Draft202012Validator
from .common import require_name

def validate_data(value, schema):
    Draft202012Validator.check_schema(schema)
    # Contracts are self-contained; validation never fetches remote references.
    def check_refs(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in {'$ref', '$dynamicRef'} and not str(child).startswith('#'):
                    raise ValueError('Only local JSON Schema references are supported')
                check_refs(child)
        elif isinstance(item, list):
            for child in item:
                check_refs(child)
    check_refs(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: str(e.path))
    if errors:
        raise ValueError('; '.join(f'{list(e.path)}: {e.message}' for e in errors[:12]))

def graph_order(graph, capabilities):
    if not isinstance(graph.get('max_concurrency',3),int) or not 1 <= graph.get('max_concurrency',3) <= 3:
        raise ValueError('max_concurrency must be an integer from 1 to 3')
    nodes = graph.get('nodes', [])
    if not nodes:
        raise ValueError('Workflow requires at least one node')
    by_id = {}
    for node in nodes:
        node_id = node.get('id')
        require_name(node_id)
        if node_id in by_id:
            raise ValueError(f'Duplicate node: {node_id}')
        by_id[node_id] = node
        if node.get('capability') not in capabilities:
            raise ValueError(f'Unknown capability: {node.get("capability")}')
        if node.get('retries', 1) not in (0, 1):
            raise ValueError('v0.1 supports zero or one retry')
        if not node.get('idempotent', False) and node.get('retries', 0):
            raise ValueError('Non-idempotent nodes cannot retry automatically')
        if not 1 <= node.get('timeout_seconds', 600) <= 86400:
            raise ValueError('Invalid node timeout')
        dependencies = node.get('depends_on', [])
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f'Duplicate dependency: {node_id}')
        for binding in node.get('bindings', {}).values():
            if isinstance(binding, dict) and set(binding) == {'from'}:
                origin = binding['from'].split('.')[0]
                if origin != 'inputs' and origin not in dependencies:
                    raise ValueError(f'Undeclared dependency in {node_id}: {origin}')
    order, visiting, visited = [], set(), set()
    def visit(node_id):
        if node_id not in by_id:
            raise ValueError(f'Missing dependency: {node_id}')
        if node_id in visiting:
            raise ValueError('Workflow contains a cycle')
        if node_id in visited:
            return
        visiting.add(node_id)
        for dependency in by_id[node_id].get('depends_on', []):
            visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)
        order.append(node_id)
    for node_id in by_id:
        visit(node_id)
    return order

def bind_inputs(node, inputs, results):
    output = {}
    for name, binding in node.get('bindings', {}).items():
        if isinstance(binding, dict) and set(binding) == {'from'}:
            parts = binding['from'].split('.')
            value = inputs if parts[0] == 'inputs' else results[parts[0]]
            for key in parts[1:]:
                if not isinstance(value, dict) or key not in value:
                    raise ValueError(f'Unresolved input binding: {binding["from"]}')
                value = value[key]
            output[name] = value
        else:
            output[name] = binding
    return output
