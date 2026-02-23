import os
import sys
import yaml
import argparse
import ast

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class AgentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.agents = {} # var_name -> {'name': str, 'domain': str, 'line': int}
        self.tools_bound = [] # [{'agent_var': str, 'tool_name': str, 'line': int}]

    def visit_Assign(self, node):
        # Look for: variable = Agent(name="...", domain="...")
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "Agent":
            kwargs = {kw.arg: kw.value.value for kw in node.value.keywords if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)}
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.agents[target.id] = {
                        "name": kwargs.get("name", "Unknown"),
                        "domain": kwargs.get("domain", "UNKNOWN_DOMAIN"),
                        "line": node.lineno
                    }
        self.generic_visit(node)

    def visit_Expr(self, node):
        # Look for: agent_var.add_tool(Tool(name="..."))
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
            if node.value.func.attr == "add_tool":
                agent_var = node.value.func.value.id if isinstance(node.value.func.value, ast.Name) else None
                if agent_var and node.value.args:
                    arg = node.value.args[0]
                    if isinstance(arg, ast.Call) and getattr(arg.func, 'id', None) == "Tool":
                        kwargs = {kw.arg: kw.value.value for kw in arg.keywords if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)}
                        tool_name = kwargs.get("name")
                        if tool_name:
                            self.tools_bound.append({
                                "agent_var": agent_var,
                                "tool_name": tool_name,
                                "line": node.lineno
                            })
        self.generic_visit(node)

def load_config(path: str):
    if not os.path.exists(path):
        print(f"{Colors.FAIL}Error: Config file not found at {path}{Colors.ENDC}")
        sys.exit(1)
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def scan_file(filepath: str, config: dict) -> bool:
    domains_config = {d['name']: d for d in config.get('domains', [])}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        print(f"{Colors.WARNING}Skipping {filepath}: Syntax error{Colors.ENDC}")
        return True

    visitor = AgentVisitor()
    visitor.visit(tree)
    
    has_violations = False
    
    for tb in visitor.tools_bound:
        agent_var = tb['agent_var']
        tool_name = tb['tool_name']
        line = tb['line']
        
        agent_info = visitor.agents.get(agent_var)
        if not agent_info:
            continue # Could be a dynamic agent, ignoring for simple static analysis
            
        agent_name = agent_info['name']
        agent_domain = agent_info['domain']
        
        domain_rules = domains_config.get(agent_domain)
        
        print(f"{Colors.OKCYAN}[AgentFirst]{Colors.ENDC} Analyzing Agent '{agent_name}' ({filepath}:{line})")
        print(f"{Colors.OKCYAN}[AgentFirst]{Colors.ENDC} -> Found Tool Injection: '{tool_name}' in domain [{agent_domain}]")
        
        if not domain_rules:
            print(f"{Colors.FAIL}❌ FATAL: STRUCTURAL VIOLATION!{Colors.ENDC}")
            print(f"Domain [{agent_domain}] is not defined in agentfirst.yaml.")
            print(f"File: {filepath}:{line}\n")
            has_violations = True
            continue
            
        allowed_actions = domain_rules.get('allowed_autonomous_actions', [])
        
        if tool_name not in allowed_actions:
            print(f"{Colors.FAIL}❌ FATAL: STRUCTURAL VIOLATION!{Colors.ENDC}")
            print(f"Agent \"{agent_name}\" belongs to domain [{agent_domain}].")
            print(f"Tool \"{tool_name}\" is not allowed for autonomous execution in [{agent_domain}].")
            print(f"Rule: Cross-domain decisions require explicit architectural approval.")
            print(f"Resolution:")
            print(f"  1. Add '{tool_name}' to `allowed_autonomous_actions` under [{agent_domain}] in agentfirst.yaml.")
            print(f"  2. Or demote agent autonomy level (Human-in-the-loop).")
            print(f"File: {filepath}:{line}\n")
            has_violations = True
        else:
            print(f"{Colors.OKGREEN}✅ VALID: Tool '{tool_name}' is architecturally compliant for [{agent_domain}].{Colors.ENDC}\n")

    return not has_violations

def main():
    parser = argparse.ArgumentParser(description="AgentFirst Architecture Validator CLI")
    parser.add_argument("scan_dir", help="Directory to scan for Agent declarations")
    parser.add_argument("--config", default="agentfirst.yaml", help="Path to agentfirst.yaml")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== AgentFirst CLI Core ==={Colors.ENDC}")
    print(f"Loaded config: {args.config}")
    print(f"Scanning directory: {args.scan_dir}\n")
    
    all_passed = True
    scanned_count = 0
    
    for root, _, files in os.walk(args.scan_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                scanned_count += 1
                if not scan_file(filepath, config):
                    all_passed = False
                    
    if scanned_count == 0:
        print(f"{Colors.WARNING}No python files found to scan.{Colors.ENDC}\n")
        sys.exit(0)

    print(f"{Colors.BOLD}--- Scan Complete ---{Colors.ENDC}")
    if all_passed:
        print(f"{Colors.OKGREEN}✅ Entropy Contained. Architectural integrity verified.{Colors.ENDC}")
        sys.exit(0)
    else:
        print(f"{Colors.FAIL}❌ Build FAILED. Structural violations detected.{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
