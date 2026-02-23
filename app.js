const translations = {
    pt: {
        nav_about: "Sobre Nós",
        nav_pilot: "Contato",
        nav_consulting: "Soluções",
        hero_badge: "Agentes Autônomos Omnichannel",
        hero_title: "Autonomia Omnichannel de ponta a ponta.<br><span class='highlight'>100% em Linguagem Natural.</span>",
        hero_subtitle: "Esqueça dashboards e ERPs complexos. A AgentFirst conecta suas plataformas (iFood, Shopee, Bancos de Dados) a Agentes Autônomos hiper-seguros. Gerencie seu estoque, financeiro e logística apenas conversando via WhatsApp ou Telegram.",
        hero_cta1: "Cadastre sua empresa",
        hero_cta2: "Ver Piloto Seguro",
        manifesto_badge: "Arquitetura & Governança",
        manifesto_title: "Como garantimos que a IA não alucine?",
        manifesto_desc: "A AgentFirst nasceu de uma pesquisa rigorosa sobre os limites da IA na Engenharia Enterprise. Nossa tese comprovou que modelos autônomos inevitavelmente degradam sistemas complexos (Entropia) se operarem sem limites matemáticos rígidos. Nós não construímos inteligência conversacional; nós arquitetamos as fundações de governança (Gatekeepers e Bounded Contexts) que garantem que a autonomia corporativa funcione 100% contida dentro da sua regra de negócio original.",
        m_thesis_title: "1. A Fundação Gatekeeper",
        m_thesis_text: "Enquanto o mercado vende 'chatbots', nós construímos Infraestrutura de Missão Crítica. A AgentFirst é a única plataforma que roda seus Agentes em um ambiente nativo de roteamento <b>Gatekeeper</b>, garantindo que a IA só acesse o que você permitir (Domain-Driven Design). Sem alucinações, sem descontos errados, sem perda de controle.",
        m_prob_title: "2. O Risco de Execução",
        m_prob_text: "Ao conceder permissões de Tool Use a modelos probabilísticos, você delega autoridade estrutural a um sistema não-determinístico. Sem um middleware rígido, ocorrem <em>Cross-Domain Invasions</em> (ex: um agente de atendimento alterando tabelas de faturamento), e as falhas críticas acontecem em frações de segundo, sem rastro auditável. O risco de receita e quebra de compliance se tornam sistêmicos.",
        m_sol_title: "3. O Gatekeeper em Runtime",
        m_sol_text: "Nossa solução é entregue de forma nativa no nível de aplicação. O <strong>AgentFirst Core</strong> atua como um proxy de controle de fluxo. Você declara Políticas e Limits no repositório via <code>agentfirst.yaml</code>. Em tempo de execução, nosso Middleware intercepta as chamadas de API geradas pela Inteligência Artificial. Se um LLM tentar uma ação fora da política, o payload não é roteado: a requisição é bloqueada e transferida para validação humana (HITL).",
        m_meth_title: "4. Deploy em 4 Semanas",
        m_meth_text: "PoCs de IA comuns sacrificam controle por agilidade. Nós fazemos o oposto. Em 30 dias, instalamos os binários do <code>agentfirst-cli</code> na sua esteira de infraestrutura, mapeamos suas APIs críticas de risco e fazemos o deploy do primeiro Agente Autônomo encapsulado pelas suas Policies. Sua engenharia assume o projeto via Github com o <em>Golden Path</em> pronto para provisionar e escalar os próximos 100 agentes com segurança default.",
        eco_badge: "Modelo Operacional",
        eco_title: "A Topologia da Solução AgentFirst",
        eco_desc: "Nós não apenas desenhamos a teoria; nós a implementamos em produção. Nosso modelo operacional é estruturado em três camadas de governança. Você adota a Fundação Gatekeeper, instancia nossos Agentes Especialistas nativos para acelerar a sua operação, ou aciona nossa divisão de arquitetos para blindar os fluxos mais críticos do seu legado.",
        agent_core_title: "AgentFirst Core",
        agent_core_desc: "O nosso 'Foundry'. A infraestrutura fundacional (Middleware + Gatekeeper) que processa NLP puro no WhatsApp/Telegram e protege suas APIs contra a Entropia Sistêmica da IA.",
        agent_retail_title: "AgentFirst Fleet",
        agent_retail_desc: "A frota estendida. Robôs pré-treinados para cenários corporativos agressivos (Retail, Logistics, Backoffice). Plug and play em cima do nosso Core, prontos para faturar no iFood ou ERP.",
        agent_sync_title: "AgentFirst SWAT",
        agent_sync_desc: "Fábrica de Missão Crítica. Nós enviamos nossos melhores engenheiros para infiltrar a sua arquitetura legada, construir o seu Agente Customizado do zero, e te entregar a operação 100% autônoma e blindada em 4 semanas.",
        pilot_title: "O Framework AgentFirst",
        pilot_desc: "Do Zero a um Agente Autônomo e em Produção em 4 Semanas.",
        pilot_sub: "Vamos mapear juntos o principal desafio operacional da sua engenharia. Nós desenhamos a arquitetura do seu primeiro Agente de missão crítica, implementamos a contenção Gatekeeper e, no Dia 30, entregamos o <em>Caminho de Ouro</em> (Golden Path) para seu time assumir o controle.",
        pilot_step1_title: "Semana 1: Triage & Arquitetura",
        pilot_step1_desc: "Mapeamento das suas APIs e desenho das Políticas Restritivas de Domínio (DDD).",
        pilot_step2_title: "Semana 2: Infiltração e Desenvolvimento",
        pilot_step2_desc: "Construção do seu primeiro Agente Autônomo encapsulado no nosso Middleware Gatekeeper.",
        pilot_step3_title: "Semana 3: Teste de Stress",
        pilot_step3_desc: "Simulamos alucinações extremas para provar que a IA está contida e não quebra seu banco de dados.",
        pilot_step4_title: "Semana 4: Handover",
        pilot_step4_desc: "Deploy em produção. Entregamos o repositório seguro (Golden Path) para sua equipe assumir a operação.",
        pilot_btn: "Agende uma reunião",
        foot_1: "AgentFirst Middleware & Core Systems.",
        foot_2: "© 2026 AgentFirst. Todos os direitos reservados."
    },
    en: {
        nav_about: "About Us",
        nav_pilot: "Contact",
        nav_consulting: "Solutions",
        hero_badge: "Omnichannel Autonomous Agents",
        hero_title: "End-to-End Omnichannel Autonomy.<br><span class='highlight'>100% in Natural Language.</span>",
        hero_subtitle: "Forget complex dashboards and legacy ERPs. AgentFirst connects your platforms (iFood, Shopee, Databases) to secure Autonomous Agents. Manage inventory, finance, and sales just by chatting on WhatsApp or Telegram.",
        hero_cta1: "Register your company",
        hero_cta2: "View Secured Pilot",
        manifesto_badge: "Architecture & Governance",
        manifesto_title: "How do we guarantee AI won't hallucinate?",
        manifesto_desc: "AgentFirst was born from rigorous research on the limits of AI in Enterprise Engineering. Our thesis proved that autonomous models inevitably degrade complex systems (Entropy) if they operate without rigid mathematical boundaries. We do not build conversational intelligence; we architect the governance foundations (Gatekeepers and Bounded Contexts) that guarantee corporate autonomy operates 100% contained within its original business rules.",
        m_thesis_title: "1. The Gatekeeper Foundation",
        m_thesis_text: "While the market sells basic 'chatbots', we build Mission-Critical Infrastructure. AgentFirst is the only platform that runs your Agents inside a native <b>Gatekeeper</b> routing environment, ensuring the AI only accesses what you explicitly permit (Domain-Driven Design). No hallucinations, no wrong pricing, no loss of control.",
        m_prob_title: "2. The Execution Risk",
        m_prob_text: "When you grant Tool Use permissions to probabilistic models, you delegate structural authority to a non-deterministic system. Without rigid middleware, <em>Cross-Domain Invasions</em> occur (e.g., a support bot independently altering billing tables), and critical failures execute in milliseconds with zero auditable trails. Revenue risk and compliance breaches become systemic problems rather than isolated incidents.",
        m_sol_title: "3. The Runtime Gatekeeper",
        m_sol_text: "Our solution ships as native application-layer code. The <strong>AgentFirst Core</strong> acts as an advanced flow-control proxy. You declare state-level Policies in your repo via <code>agentfirst.yaml</code>. In runtime, our Middleware intercepts AI-generated API payloads. If an LLM intent violates an active policy, the payload is never routed to your backend: the request is physically blocked and escalated to human validation (HITL).",
        m_meth_title: "4. 4-Week Deployment",
        m_meth_text: "Standard AI PoCs trade control for speed. We do the exact opposite. In 30 days, we install the <code>agentfirst-cli</code> binaries into your deployment pipeline, map your critical risk APIs, and push to production your first Autonomous Agent fully insulated by Gatekeeper policies. Your engineering team receives the Github repos with a secure 'Golden Path' architecture ready to provision the next 100 agents securely.",
        eco_badge: "Operational Model",
        eco_title: "The AgentFirst Solution Topology",
        eco_desc: "We don't just design the theory; we implement it in production. Our operational model is structured into three governance layers. You adopt the Gatekeeper Foundation, instantiate our native Specialist Agents to accelerate your operation, or trigger our architect division to shield the most critical workflows of your legacy systems.",
        agent_core_title: "AgentFirst Core",
        agent_core_desc: "Our 'Foundry'. The foundational infrastructure (Middleware + Gatekeeper) that processes pure NLP over WhatsApp/Telegram and shields your APIs against Systemic AI Entropy.",
        agent_retail_title: "AgentFirst Fleet",
        agent_retail_desc: "The extended fleet. Pre-trained autonomous robots for aggressive corporate scenarios (Retail, Logistics, Backoffice). Plug and play on top of our Core, ready to operate your ERP.",
        agent_sync_title: "AgentFirst SWAT",
        agent_sync_desc: "Mission Critical Deployment. We deploy our best engineers to infiltrate your legacy architecture, build your custom Agent from the ground up, and deliver a fully secured, autonomous operation in exactly 4 weeks.",
        pilot_title: "The AgentFirst Framework",
        pilot_desc: "From Zero to a Governed, Production-Ready Autonomous Agent in 4 Weeks.",
        pilot_sub: "Let's jointly map your engineering team's main operational challenge. We design the architecture for your first mission-critical Agent, implement Gatekeeper containment, and on Day 30, we hand over the <em>Golden Path</em> for your team to take control.",
        pilot_step1_title: "Week 1: Triage & Architecture",
        pilot_step1_desc: "Mapping your critical APIs and designing Restrictive Domain Policies (DDD).",
        pilot_step2_title: "Week 2: Infiltration & Development",
        pilot_step2_desc: "Building your first Autonomous Agent encapsulated inside our Gatekeeper Middleware.",
        pilot_step3_title: "Week 3: Stress-Testing",
        pilot_step3_desc: "We simulate extreme AI hallucinations to prove the system is fully contained and secure.",
        pilot_step4_title: "Week 4: Handover",
        pilot_step4_desc: "Production deploy. We hand over the secure repository (Golden Path) for your team to take over.",
        pilot_btn: "Schedule a meeting",
        foot_1: "AgentFirst Middleware & Core Systems.",
        foot_2: "© 2026 AgentFirst. All rights reserved."
    }
};

const terminalData = {
    pt: [
        "👤 [Usuário via Telegram]: \"Muda o preço da Ração Royal Canin 15kg pra R$ 15,00. Promoção de hoje!\"",
        "🤖 [AgentFirst Core] Intenção detectada: 'PRICE_UPDATE'.",
        "🤖 [AgentFirst Core] Roteando para AgentFirst Retail (Especialista iFood/Shopee)...",
        "",
        "<span class='t-cyan'>🛡️ [AgentFirst Gatekeeper] Interceptando chamada de mutação de API...</span>",
        "📦 [RetailAgent] Solicitando alteração de preço no ERP/iFood: SKU RC-15KG para R$ 15.00",
        "",
        "<span class='t-warn'>⚠️ POLICY TRIGGERED: RESTRICT_PRICE_DROP</span>",
        "Queda de preço no SKU RC-15KG excede o limite seguro de 20.0%. (Atual: R$ 349.90, Solicitado: R$ 15.00)",
        "<span class='t-green'>✅ SYSTEMIC ENTROPY BLOCKED.</span>",
        "",
        "<span class='t-red'>🚨 DECISION OVERRIDE REQUIRED 🚨</span>",
        "Notificando Gerente da Lollapet via WhatsApp para autorização (HITL)...",
        "Aprovar a execução deste payload no iFood e Shopee? [y/N]: <span class='typewriter-cursor'>█</span>",
        "<span class='t-red'>❌ OVERRIDE REJECTED: Ação negada pelo humano.</span>",
        "🛒 [RetailAgent] 🔴 Operação abortada com segurança pelo Gatekeeper."
    ],
    en: [
        "👤 [User via Telegram]: \"Change the Royal Canin 15kg dog food price to $ 15.00. Flash sale!\"",
        "🤖 [AgentFirst Core] Intent detected: 'PRICE_UPDATE'.",
        "🤖 [AgentFirst Core] Routing to AgentFirst Retail (iFood/Shopee Specialist)...",
        "",
        "<span class='t-cyan'>🛡️ [AgentFirst Gatekeeper] Intercepting API mutation call...</span>",
        "📦 [RetailAgent] Requesting price update on ERP/iFood: SKU RC-15KG to $ 15.00",
        "",
        "<span class='t-warn'>⚠️ POLICY TRIGGERED: RESTRICT_PRICE_DROP</span>",
        "Price drop for SKU RC-15KG exceeds the safe limit of 20.0%. (Current: $ 349.90, Requested: $ 15.00)",
        "<span class='t-green'>✅ SYSTEMIC ENTROPY BLOCKED.</span>",
        "",
        "<span class='t-red'>🚨 DECISION OVERRIDE REQUIRED 🚨</span>",
        "Notifying Lollapet Manager via WhatsApp for authorization (HITL)...",
        "Approve this payload execution on iFood and Shopee? [y/N]: <span class='typewriter-cursor'>█</span>",
        "<span class='t-red'>❌ OVERRIDE REJECTED: Action denied by human.</span>",
        "🛒 [RetailAgent] 🔴 Operation safely aborted by Gatekeeper."
    ]
};

document.addEventListener('DOMContentLoaded', () => {
    let currentLang = 'pt';
    let lineIndex = 0;
    let typingTimeout;
    const terminalContainer = document.getElementById('typed-terminal');

    function applyTranslations(lang) {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (translations[lang][key]) {
                el.innerHTML = translations[lang][key];
            }
        });

        document.getElementById('lang-pt').classList.toggle('active', lang === 'pt');
        document.getElementById('lang-en').classList.toggle('active', lang === 'en');
        document.documentElement.lang = lang;
    }

    function startTerminal() {
        terminalContainer.innerHTML = '';
        lineIndex = 0;
        clearTimeout(typingTimeout);
        typeLine();
    }

    function typeLine() {
        const lines = terminalData[currentLang];
        if (lineIndex < lines.length) {
            const line = lines[lineIndex];
            const div = document.createElement('div');

            if (line.includes('[y/N]:')) {
                div.innerHTML = line;
                terminalContainer.appendChild(div);

                typingTimeout = setTimeout(() => {
                    const cursor = div.querySelector('.typewriter-cursor');
                    if (cursor) {
                        cursor.classList.remove('typewriter-cursor');
                        cursor.innerHTML = 'n <span class="typewriter-cursor">█</span>';

                        typingTimeout = setTimeout(() => {
                            if (div.querySelector('.typewriter-cursor')) {
                                div.querySelector('.typewriter-cursor').remove();
                            }
                            lineIndex++;
                            typeLine();
                        }, 800);
                    }
                }, 1500);
            } else {
                div.innerHTML = line;
                terminalContainer.appendChild(div);
                lineIndex++;

                terminalContainer.scrollTop = terminalContainer.scrollHeight;

                const delay = line.trim() === "" ? 200 : Math.random() * 400 + 100;
                typingTimeout = setTimeout(typeLine, delay);
            }
        }
    }

    // Initialize Default Language
    applyTranslations(currentLang);
    setTimeout(startTerminal, 1000);

    // Language Toggle Listeners
    document.getElementById('lang-pt').addEventListener('click', () => {
        if (currentLang !== 'pt') {
            currentLang = 'pt';
            applyTranslations('pt');
            startTerminal();
        }
    });

    document.getElementById('lang-en').addEventListener('click', () => {
        if (currentLang !== 'en') {
            currentLang = 'en';
            applyTranslations('en');
            startTerminal();
        }
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');

            if (href === '#') {
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
                return;
            }

            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});
