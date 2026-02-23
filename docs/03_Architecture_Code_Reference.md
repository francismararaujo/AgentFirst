# AgentFirst: Architecture as Code Reference

## 1. The Operationalizing of Governance
The key differentiator of the AgentFirst methodology is that it translates strategic governance into enforceable, deterministic software architectures. We move from "Slides to CI/CD."

This is achieved via the **AgentFirst Core** stack. 

## 2. Component: `agentfirst.yaml` (Infrastructure as Strategy)
This configuration file is the heart of the Decision Architecture. 

During the *Discovery* phase of the Secured Pilot, the Enterprise Architect explicitly maps the **Bounded Contexts** (Domains) of the organization.

**File Structure Example:**
```yaml
domains:
  - name: CUSTOMER_SERVICE
    owner: "atendimento@empresa.com"
    allowed_autonomous_actions:
      - "get_order_status"
      - "send_faq_link"
      
  - name: FINANCE
    owner: "cfo@empresa.com"
    isolation_level: STRICT
    allowed_autonomous_actions: 
      - "refund_order_api"
    
policies:
  - rule: "STRICT_DOMAIN_ISOLATION"
    description: "Agents cannot bind to tools outside their declared domain."
    action: BLOCK
```
* **Why it matters:** Engineers do not need to guess what is safe. They declare their Agent's domain, and the system inherits the constraints.

## 3. Component: The AI Gatekeeper Middleware
The Gatekeeper is a code-level middleware layer that sits between the LLM orchestration (e.g., Langchain, Vercel AI SDK) and the company's internal APIs. 

**Behavior Pipeline:**
1. The AI Agent forms an intent to call a Tool (e.g., `refund_order_api`).
2. The Gatekeeper intercepts the outbound request.
3. The Gatekeeper evaluates the Agent's identity and Domain against the `agentfirst.yaml`.
4. **Outcome A (Allowed):** If the Agent is in `FINANCE`, the API call proceeds autonomously.
5. **Outcome B (Blocked/Escalated):** If the Agent is in `CUSTOMER_SERVICE` and lacks privileges, the Gatekeeper blocks the execution and triggers a *Decision Override* (Human-in-the-loop validation) or throws an Entropy Alarm.

## 4. Component: The AgentFirst CLI (`af-cli`)
The CLI is a static analysis engine designed to shift governance to the **left** of the development lifecycle (Shift-Left Security/Architecture).

* **Placement:** It runs as a GitHub Action or local pre-commit hook.
* **Function:** It parses the Abstract Syntax Tree (AST) of the engineers' code before it is merged into the main branch. It detects `Agent` instantiations and `Tool` bindings.
* **Enforcement:** If a developer attempts to bind a high-risk Tool to an Agent in a low-privilege domain, the CLI fails the build. 

**"Entropy is contained before it ever reaches Staging."**
