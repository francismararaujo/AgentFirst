# Agent Discovery Workshop Read Out - AgentFirst2

**Date:** February 2, 2026
**Project:** AgentFirst2 (Omnichannel Retail AI Platform)
**Version:** 1.0

---

## 1. Executive Summary

This document summarizes the "Discovery Workshop" findings for the AgentFirst2 project. The primary goal is to build an **Enterprise-Grade Omnichannel AI Platform** that allows retail operations (starting with iFood integration) to be managed 100% via Natural Language, without traditional interfaces (No-UI).

The MVP focuses on the **Retail Domain** (specifically iFood integration) via **Telegram**, replacing dashboards and apps with a conversational agent (Brain) powered by Claude 3.5 Sonnet.

---

## 2. Use Case Definition

### 2.1 Scope & Prioritization
Unlike the reference pharmaceutical project (which focused on prescription OCR and drug interactions), AgentFirst2 prioritizes **operational efficiency in food delivery retail**.

**Selected Use Case (MVP):**
*   **Name:** "Operations Copilot" (Retail Agent)
*   **Goal:** Enable a store manager to monitor, confirm, and manage iFood orders entirely through natural language on messaging apps (Telegram).
*   **Primary User:** Store Manager / Franchise Owner.
*   **Business Value:** reduce reaction time to orders, allow management on-the-go (mobile), reduce dependency on iFood Portal access.

### 2.2 User Journey
1.  **Notification:** Agent proactively notifies user of new event (New Order, Cancellation Request) on Telegram.
    *   *"📦 Novo pedido #12348 no iFood: 2x Hambúrguer - R$ 95,00"*
2.  **Action:** User responds naturally.
    *   *"Confirma e manda pra cozinha"*
3.  **Execution:** Agent interprets intent, executes API call to iFood (Acknowledge + Confirm + Dispatch).
4.  **Feedback:** Agent confirms success.
    *   *"✅ Pedido #12348 confirmado e enviado para produção."*
5.  **Query:** User asks for consolidation.
    *   *"Quanto faturei hoje até agora?"*
6.  **Insights:** Agent queries sales data and responds.
    *   *"💰 R$ 1.250,00 em 15 pedidos hoje."*
7.  **Stock Update:** User takes a photo of an invoice.
    *   *"📸 [Envia Foto da Nota Fiscal]"*
8.  **Processing:** Agent analyzes image, extracts items, and confirms.
    *   *"Recebi a nota de R$ 450,00. Identifiquei: 50x Pães, 20x Carnes. Estoque atualizado! ✅"*

### 2.3 Data Sources & Integrations
| Source | Type | Usage | Status |
| :--- | :--- | :--- | :--- |
| **iFood API** | External API | Order polling, management, menu, financial data. | **CRITICAL (Implementing)** |
| **User Memory** | DynamoDB | Context retention across channels (Email-based). | **Ready** |
| **Business Rules** | Knowledge Base | Operational rules (e.g., auto-confirm logic). | **Planned** |

---

## 3. Gap Analysis (vs. Drogaria Araujo Reference)

Comparing the current AgentFirst2 architecture with the reference "Drogaria Araujo" architecture, the following gaps and opportunities were identified:

### 3.1 Missing Capabilities (Consider for Post-MVP)
1.  **RAG (Retrieval Augmented Generation):**
    *   *Reference:* Uses Kendra/OpenSearch to search operational manuals and drug leaflets.
    *   *AgentFirst:* Currently relies on structured DynamoDB memory.
    *   *Recommendation:* Implement RAG for "Store Procedures" or "iFood Policy" queries (e.g., "How do I dispute a chargeback?").

2.  **Frontend Demo (Web):**
    *   *Reference:* Includes an ECS-hosted frontend.
    *   *AgentFirst:* Purely headless (Telegram-only for MVP).
    *   *Recommendation:* Keep headless for now, as "No-UI" is a core principle.

### 3.2 Planned Scope Additions (Gap Filling)
1.  **Inventory OCR (Vision):**
    *   *Requirement:* User needs to upload photos of invoices (Notas Fiscais) to update stock.
    *   *Solution:* Use **Claude 3.5 Sonnet (Vision)** via Bedrock to extract line items from photos sent via Telegram and automatically call `update_inventory`.


### 3.2 Architectural Alignment
Both projects share a robust **AWS Serverless** backbone:
*   **Compute:** AWS Lambda (Python) vs. Reference ECS/Lambda.
*   **LLM:** Bedrock (Claude 3.5 Sonnet) - Aligned.
*   **Data:** DynamoDB - Aligned.
*   **Integration:** API Gateway - Aligned.

---

## 4. Project Execution Plan

### 4.1 Timeline (5 Weeks MVP)
| Week | Focus | Key Deliverables |
| :--- | :--- | :--- |
| **1** | **Core Infra** | DynamoDB, Lambda, Telegram Adapter, user Auth. (Done) |
| **2** | **Brain & Omnichannel** | NLP Universal, Context Management, Agent Routing. (Done) |
| **3** | **iFood Connector** | **CRITICAL**: polling, ack, order mgmt (105+ criteria). (In Progress) |
| **4** | **Testing & CI/CD** | 100% Coverage, Property-based tests, Deployment pipeline. |
| **5** | **Homologation** | iFood Certification, Documentation, Launch. |

### 4.2 Next Steps (Immediate)
1.  Complete the **iFood Connector** implementation (focus on Polling and Event Acknowledgment loops).
2.  Validate the **Supervisor (HITL)** flow for high-value decisions (e.g., cancelling an order).
3.  Generate the **Homologation Video** for iFood approval.

---

## 5. Appendix: Resource Requirements

| Resource Type | Description | Status |
| :--- | :--- | :--- |
| **LLM Model** | Claude 3.5 Sonnet (Bedrock) | ✅ Active |
| **Messaging** | Telegram Bot Token | ✅ Active |
| **Partner API** | iFood Merchant API Creds | ✅ Active |
| **Compute** | AWS Lambda (512MB) | ✅ Active |
| **Storage** | DynamoDB (On-Demand) | ✅ Active |

---

*Generated by Antigravity Agent based on project analysis and comparison with "Agent Discovery Workshop Read Out.pdf"*
