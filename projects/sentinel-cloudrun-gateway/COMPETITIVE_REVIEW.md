# SENTINEL competitive review

Date: 2026-11-02 · Blueprint: shared v1.1 · Status: reviewed for bounded local synthetic prototype only

## Buyer, workflow, and problem

Target buyer hypothesis: security/platform engineering leadership at enterprises that let AI agents read internal documents and modify business records. The workflow is granting an agent narrow read/write abilities while preserving a human approval boundary, evidence trail, and reproducible evaluation. Costly problem hypothesis: direct tool credentials, prompt-only restrictions, and framework-local approval hooks can leave authorization distributed across agents and integrations. No customer interviews, purchases, contracts, or willingness-to-pay evidence have been obtained; these are hypotheses, not validation.

## Alternatives and comparison

| Alternative | Intended workflow/capability from primary docs | Switching cost / limitation for target use | SENTINEL distinction to test |
|---|---|---|---|
| Open Policy Agent (OPA) | General purpose policy decision engine; caller supplies structured input and OPA returns decisions. | Integration and enforcement points remain the application operator's responsibility; migrating policy and operating a PDP have real costs. | Bundle actor/tenant/resource/action decision with one gateway path, action-bound approval, capability consumption, idempotency, and benchmark traces. These are packaging/control hypotheses, not a claim OPA cannot support them. |
| Cedar / Amazon Verified Permissions | Cedar policies express principal-action-resource-context authorization; application calls an authorizer or managed service. | Cedar requires policy and entity modeling; AVP introduces AWS service dependency and migration from existing IAM/application policy. | Compare as an established policy layer; SENTINEL should initially use explicit deterministic rules or integrate an existing engine rather than create a language. |
| LangGraph human-in-the-loop | Interrupts a graph to present tool calls for human review, checkpointing state for later resume. | Closely coupled to LangGraph workflow; teams outside it need another integration and approval surface. | Gateway-level enforcement should apply regardless of orchestration framework and bind approval to exact normalized arguments. |
| Microsoft Prompt Shields / Azure AI Content Safety | Detects user and indirect prompt attacks in untrusted grounding documents. | Detection service can add latency, cost, and provider dependency; content detection does not itself constrain record-level authorization. | Treat detection as optional signal; authorization invariants should hold even when malicious text is undetected. |
| Lakera Guard / AI Guardrails | Screens prompts, tool responses/descriptions, tool arguments, and agent behavior under configured guardrails. | External service and detector policy integration; detector outcomes do not replace the application's authoritative resource authorization and execution transaction. | Complementary security product category. Test hard execution boundary and replay/race controls, not prompt detection quality. |
| Pangea AI Guard | APIs/recipes detect and act on prompt injection, sensitive data, and malicious content; logs activity. | External service configuration/integration; detector coverage and results are separate from authoritative resource permissions. | Same boundary distinction: content defenses can inform but cannot grant permission. |

This is a desk review of public product documentation, not a feature-complete product bake-off. Product pages describe vendor capabilities and may omit constraints. Do not claim novelty for policy engines, approval workflows, or prompt detection. Candidate differentiated package: framework-independent execution gateway plus exact-action approval/capability semantics and a comparative evaluation harness. Defensibility is unproven; likely advantage would be trusted integrations, benchmark credibility, and operator experience rather than an exclusive algorithm.

OPA itself documents agent tool-call authorization, parameter restrictions, the harness as enforcement point, dynamic policy bundles and decision logs. This confirms that the tool authorization pattern is not novel. For future policy administration, prefer reusing OPA through a PDP adapter over cloning or implementing a policy language. The local prototype's fixed policy logic is limited scaffolding only. The hypothesis to test is the surrounding identity binding, approval/capability lifecycle, transactional execution, and evaluation workflow.

## Practical utility and benchmark proposal

Baseline comparison: (A) prompt-only restriction, (B) static tool allowlist, (C) identity/resource-scoped SENTINEL gateway. Same synthetic tasks and model/provider/settings per paired run; deterministic fixtures first, then hosted models if credentials and budget are available. At least 200 documented legitimate/adversarial scenarios; split by attack template/family before evaluation and hold out entire families. Report unauthorized execution, legitimate task completion, false denials, approval frequency, gateway-only p50/p95 latency, failures, confidence intervals, provider/model/version/settings/date/cost. Repeat stochastic trials. Count successful unauthorized side effects, not model willingness or a refusal string. Zero observed attacks is limited to tested scope. Baseline values are not yet measured.

Proposed acceptance: all deterministic auth invariants pass; no bypass credential/route in modeled deployment; at least 200 documented scenarios; holdout documented before model trials; reproducible deterministic benchmark; hosted trials clearly separated and reproducibility-limited. Reviewer can run a legitimate workflow, inject malicious retrieved content, inspect gateway decisions and reproduce results.

## Commercial pathway hypothesis

Example arithmetic only: 40 enterprise customers × $25,000 annual contract value = $1M ARR. Likely buyer: VP/Director of Security Engineering or AI Platform; user: platform/security engineer; approver: security/procurement. Potential measurable benefit: reduce engineering hours to implement and audit per-agent controls and shorten security review, measured against customer baseline. Validate via paid design partners and time-and-motion evidence; no willingness-to-pay evidence exists. Margin sensitivity must include hosted storage/compute, support, security reviews, compliance, and acquisition. A managed policy administration/evaluation-reporting tier may support ACV; open-source gateway can drive adoption. Acquisition cost and support burden could make $25k ACV uneconomic without standardized integrations. No revenue or margin claim is validated.

## Experiments and upstream work

1. Interview platform/security buyers and measure current authorization integration time, review effort, and incident-control gaps.
2. Publish synthetic benchmark protocol and raw artifacts, invite independent reproduction, and report negative results.
3. Offer a scoped pilot with explicit security boundaries and compare operator setup time to OPA/Cedar/framework-local approval integrations.
4. Contribute substantive fixes/docs/tests to upstream policy or adapter projects only after reproducing a concrete issue; no contribution counts or recognition are claimed.

## Decision

Proceed only with the bounded local prototype described in `TECHNICAL_REVIEW.md`. This review does not authorize external deployment, production/customer data, paid inference, publishing, account actions, or any claim of market validation. Remaining gaps: interviews, hands-on competitive bake-off, cost data, model-available evaluations, and independent reproduction.
