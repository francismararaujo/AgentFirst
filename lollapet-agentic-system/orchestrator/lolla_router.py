from af_core.gatekeeper import AgentFirstGatekeeper
from domain_agents.inventory_agent import InventoryParserAgent
from domain_agents.ecommerce_agent import EcommerceUpdaterAgent

class Colors:
    HEADER = '\033[95m'
    OKCYAN = '\033[96m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class LollaRouter:
    """The Orchestrator Agent. Doesn't do the work, just routes it."""
    def __init__(self):
        # The central governance engine is instantiated once for the system
        self.gatekeeper = AgentFirstGatekeeper(config_path="agentfirst.yaml")
        
        # The specialists
        self.inventory_specialist = InventoryParserAgent()
        self.ecommerce_specialist = EcommerceUpdaterAgent()

    def process_incoming_xml(self, filepath):
        print(f"\n{Colors.HEADER}{Colors.BOLD}🤖 [Lolla-Router] Received new request to process: {filepath}{Colors.ENDC}")
        print(f"🤖 [Lolla-Router] Routing to Inventory Specialist...")
        
        # Step 1: Route to Inventory Agent
        parsed_data = self.inventory_specialist.process_xml(filepath, self.gatekeeper)
        
        if not parsed_data:
            print("🤖 [Lolla-Router] Workflow halted. Parsing failed or blocked.")
            return
            
        print(f"🤖 [Lolla-Router] Data extracted. Routing {len(parsed_data)} items to Ecommerce Specialist to sync platforms...")
        
        # Step 2: Route to Ecommerce Agent
        success = self.ecommerce_specialist.push_to_platforms(parsed_data, self.gatekeeper)
        
        if success:
            print(f"\n{Colors.OKCYAN}🤖 [Lolla-Router] Workflow Completed Successfully. Lollapet inventory is synced!{Colors.ENDC}\n")
        else:
            print(f"\n{Colors.FAIL}🤖 [Lolla-Router] Workflow FAILED. Action was intercepted by AgentFirst Governance.{Colors.ENDC}\n")
