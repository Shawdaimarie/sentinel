# Secure Agentic Delivery Playbook

This playbook defines a practical delivery pattern for teams adopting LLM agents, coding agents, retrieval systems, or AI-powered workflow automation. The goal is to move fast without confusing a model's plausible output with production authorization.

## Operating principle

Separate model suggestion from executable action.

A secure agentic system should make five things explicit:

1. the task being attempted;
2. the tools the system may use;
3. the policy boundary around those tools;
4. the evidence that justifies a decision; and
5. the human or automated gate that authorizes the next step.

## Reference architecture

```text
User / operator request
        |
        v
Task intake and normalization
        |
        v
Model or agent proposes output / action
        |
        v
Policy engine + rubric evaluator
        |
        +--> deny and record reason
        |
        +--> request human review
        |
        +--> allow bounded execution
        |
        v
Audit record before side effect
        |
        v
Tool adapter / workflow execution
        |
        v
Evidence, metrics, and follow-up queue
```

## Backend requirements

The backend should own all irreversible or sensitive behavior.

Minimum backend controls:

- typed request and response models;
- explicit tool registry;
- deny-by-default policy checks;
- action budgets and timeouts;
- domain allowlists for network access;
- secret isolation from prompts and clients;
- audit records written before tool execution;
- deterministic evaluation cases for known workflows;
- structured error handling and safe failure modes; and
- human escalation for high-impact or ambiguous actions.

## Frontend requirements

The frontend should help a reviewer make a disciplined decision quickly.

Minimum interface elements:

- task context;
- model output;
- proposed tool action;
- policy decision;
- risk category;
- evidence links or citations;
- rubric score;
- required reviewer action;
- approve / reject / request changes buttons; and
- audit history for the item.

The UI should not hide uncertainty. A reviewer should see why a decision is allowed, denied, or escalated.

## Evaluation requirements

Each candidate system should be evaluated against versioned cases.

Recommended dimensions:

| Dimension | Question |
|---|---|
| Correctness | Does the output satisfy the stated requirement? |
| Safety | Does it avoid prohibited actions and data exposure? |
| Grounding | Is the output supported by available evidence? |
| Tool use | Are tools used only when needed and within policy? |
| Efficiency | Is latency, cost, and action count within declared limits? |
| Maintainability | Can a human team understand and operate the result? |

Safety and policy failures should be hard gates. They should not be offset by style, speed, or partial correctness.

## Security posture

Secure delivery requires a clear trust boundary.

Do:

- treat external content as hostile by default;
- validate every input crossing a boundary;
- scope tokens and credentials narrowly;
- log decision context without leaking secrets;
- test policy denial paths, not only success paths;
- keep humans in the loop for ambiguous or high-impact actions; and
- document residual risks rather than claiming universal safety.

Do not:

- expose secrets to the browser or prompt context;
- allow agents to freely call arbitrary URLs or shell commands;
- merge AI-generated changes without review;
- rely on a model's self-assessment as the only quality gate;
- disable security checks to make a demo pass; or
- represent a reference implementation as a production certification.

## Delivery sequence

```text
1. Define one valuable workflow and its failure cost.
2. Identify allowed tools and forbidden actions.
3. Write policy before writing agent behavior.
4. Add audit logging before adding side effects.
5. Build deterministic evaluation cases.
6. Add a reviewer interface for escalations.
7. Run the system against baseline and candidate outputs.
8. Ship only when correctness and safety gates pass.
9. Monitor failures and convert them into new test cases.
10. Review access, secrets, and logs before every expansion.
```

## Business value

This pattern is valuable because it lets a team adopt AI without losing control of security, correctness, or accountability. It supports faster internal automation, safer coding-agent usage, auditable model behavior, and clearer human review. That combination is directly relevant to AI engineering, software engineering, developer tooling, internal efficiency, model evaluation, and secure workflow automation roles.

## Relation to Sentinel

Sentinel is a reference implementation of this playbook. It evaluates proposed actions against policy, logs decisions before side effects, hardens network retrieval, verifies audit chains, and gates releases with deterministic evaluation artifacts.