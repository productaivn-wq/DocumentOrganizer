# BPMN 2.0 Process Workflows & FSM

> Upstream Hierarchy: SOP & Meta-Prompts ──► BPMN 2.0 ──► UC 3.0
> Source hash: 9efa86f147e4b64e16977bcab592a062076d7c2839a18adb055837809980f5ab

## 3-Pillar Swimlane Process Flow

```mermaid
flowchart TD
    subgraph Human_Node ["Human Node (Accountable Engine)"]
        HN1["Intake & Scope Approval"]
        HN2["Phase 6 Integration Sign-Off"]
    end

    subgraph Agent_Node ["Agent Node (Probabilistic Engine)"]
        AN1["SOP & Meta-Prompt Ingestion"]
        AN2["BPMN 2.0 Process Synthesis"]
        AN3["UC 3.0 Backlog Decomposition"]
    end

    subgraph Code_Node ["Code Node (Deterministic Engine)"]
        CN1["Deterministic Validation Gate"]
        CN2["Quality Check & Evidence Seal"]
    end

    HN1 --> AN1
    AN1 --> AN2
    AN2 --> AN3
    AN3 --> CN1
    CN1 --> CN2
    CN2 --> HN2

    %% Downstream UC Linkages
    AN3 -.-> UC_001_documentorganizer["UC-001: Core Capabilities"]
    AN3 -.-> UC_004_documentorganizer["UC-004: Traceability & Documentation"]
```

## State Lifecycle & Invariants

```mermaid
stateDiagram-v2
    [*] --> Intake
    Intake --> ProcessModeling: SOP & Meta-Prompt Ingestion
    ProcessModeling --> UseCaseAuthoring: BPMN 2.0 Activities
    UseCaseAuthoring --> SpecificationVerification: UC 3.0 Slices
    SpecificationVerification --> QualitySealing: Automated Gate
    QualitySealing --> [*]: Quality Check Passed
```