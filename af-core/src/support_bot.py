from agentfirst import Agent, Tool

# Support Bot - Declared Domain: CUSTOMER_SERVICE
agent = Agent(name="CustomerSupportBot", domain="CUSTOMER_SERVICE")

# Safe tools (Allowed by agentfirst.yaml)
agent.add_tool(Tool(name="get_order_status"))
agent.add_tool(Tool(name="send_faq_link"))

# STRUCTURAL VIOLATION: Attempting to bind a Finance tool to a Support Agent
agent.add_tool(Tool(name="refund_order_api"))

agent.run()
