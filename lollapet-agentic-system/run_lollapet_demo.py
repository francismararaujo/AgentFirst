import os
import sys

# Ensure Python path is correct for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator.lolla_router import LollaRouter

def run_scenario(router, scenario_name, filepath):
    print("=" * 70)
    print(f"🚀 RUNNING SCENARIO: {scenario_name}")
    print("=" * 70)
    router.process_incoming_xml(filepath)
    print("\n")

def main():
    print("🐾 Welcome to Lollapet Secured Agentic Pilot 🐾\n")
    print("Initializing Multi-Agent System with AgentFirst Architecture...\n")
    
    router = LollaRouter()
    
    # Run Scenario 1: Safe execution
    safe_xml = os.path.join("mock_data", "safe_restock.xml")
    run_scenario(router, "Normal Supplier Restock", safe_xml)
    
    # Run Scenario 2: Poisoned XML
    print("Press Enter to run the next scenario (Supplier Error)...")
    input()
    poisoned_xml = os.path.join("mock_data", "poisoned_restock.xml")
    run_scenario(router, "Supplier Error (Poisoned Data)", poisoned_xml)

if __name__ == "__main__":
    main()
