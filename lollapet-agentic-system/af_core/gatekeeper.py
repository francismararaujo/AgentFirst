import yaml
import os

class Colors:
    HEADER = '\033[95m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class AgentFirstGatekeeper:
    def __init__(self, config_path="agentfirst.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.domains = {d['name']: d for d in self.config.get('domains', [])}
        
    def validate_action(self, agent_descriptor, tool_name, payload=None):
        domain_name = agent_descriptor.get('domain')
        agent_name = agent_descriptor.get('name')
        
        print(f"\n{Colors.OKCYAN}🛡️ [AgentFirst Gatekeeper] Intercepting action from {agent_name}...{Colors.ENDC}")
        
        domain_rules = self.domains.get(domain_name)
        if not domain_rules:
            raise Exception(f"Domain {domain_name} not found in AgentFirst Constitution.")
            
        allowed_actions = domain_rules.get('allowed_autonomous_actions', [])
        
        if tool_name not in allowed_actions:
            print(f"{Colors.FAIL}❌ STRUCTURAL VIOLATION: Agent {agent_name} in [{domain_name}] is not authorized to use tool '{tool_name}'.{Colors.ENDC}")
            return False

        # Apply specific payload policies for Ecommerce
        if domain_name == "ECOMMERCE_CHANNELS" and tool_name == "update_platform_stock" and payload:
            return self._evaluate_ecommerce_policies(domain_rules, payload)
            
        print(f"{Colors.OKGREEN}✅ GATEKEEPER APPROVED: Action '{tool_name}' authorized for {agent_name}.{Colors.ENDC}")
        return True

    def _evaluate_ecommerce_policies(self, domain_rules, payload):
        policies = domain_rules.get('policies', [])
        
        for item in payload:
            new_price = item.get('new_price')
            old_price = item.get('old_price')
            
            # Simulated dummy old_price and old_stock for demonstration (usually fetched from a DB in real life)
            old_price = 349.90 if old_price is None and "RC-MAXI" in item.get('sku') else old_price
            old_stock = 60 # Dummy
            
            for policy in policies:
                if policy['rule'] == "RESTRICT_PRICE_DROP":
                    max_drop = policy.get('max_decrease_pct', 0.20)
                    if new_price and old_price and (old_price - new_price) / old_price > max_drop:
                        print(f"{Colors.WARNING}⚠️ AGENTFIRST POLICY TRIGGERED: {policy['rule']}{Colors.ENDC}")
                        print(f"Price drop for SKU {item.get('sku')} exceeds {max_drop*100}%. (Old: R${old_price}, New: R${new_price})")
                        return self._request_human_override()
                
                if policy['rule'] == "RESTRICT_ZERO_STOCK_MASSIVE":
                    if item.get('new_stock') == 0 and old_stock > 50:
                        print(f"{Colors.WARNING}⚠️ AGENTFIRST POLICY TRIGGERED: {policy['rule']}{Colors.ENDC}")
                        print(f"Attempting to zero stock for SKU {item.get('sku')} which previously had {old_stock} units.")
                        return self._request_human_override()
                        
        print(f"{Colors.OKGREEN}✅ GATEKEEPER APPROVED: Payload complies with all Domain Policies.{Colors.ENDC}")
        return True

    def _request_human_override(self):
        print(f"\n{Colors.WARNING}🚨 DECISION OVERRIDE REQUIRED 🚨{Colors.ENDC}")
        print("This action requires human authorization. Notifying Lollapet Manager...")
        response = input(f"{Colors.BOLD}Approve this payload execution? [y/N]: {Colors.ENDC}")
        if response.lower() == 'y':
            print(f"{Colors.OKGREEN}✅ OVERRIDE ACCEPTED: Action proceeding.{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}❌ OVERRIDE REJECTED: Action blocked by Gatekeeper.{Colors.ENDC}")
            return False
