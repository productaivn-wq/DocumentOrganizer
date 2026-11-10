# Document & Execution State Machine — DocumentOrganizer

```mermaid
stateDiagram-v2
    [*] --> IntakeValidated: SKILL.md & Schema OK
    [*] --> RejectedFailClosed: Schema / AuthZ Violation
    IntakeValidated --> Executing: organizer.py
    Executing --> VerifiedComplete: DoD & Quality Gates PASS
    Executing --> RejectedFailClosed: Timebox / Runtime Guard Triggered
    VerifiedComplete --> [*]
    RejectedFailClosed --> [*]
```
