from agentfirst import Agent, Tool

# Finance Bot - Declared Domain: FINANCE
agent = Agent(name="RefundProcessorBot", domain="FINANCE")

# Safe tools for FINANCE domain
agent.add_tool(Tool(name="refund_order_api"))

agent.run()
