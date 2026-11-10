# Entity-Relationship Diagram

> Source hash: 11ee2b55a76349a8b5a1aca5e8788069f61c953b5ad14aa191c2b744bbe6f49f

```mermaid
erDiagram
    DocumentNode {
        string node_id
        Path file_path
        string zone
        string category
        Set tags
        Set dependencies
        Dict metadata
    }
    TraceabilityProfile {
        Path file_path
        Set use_cases
        Set functional_requirements
        Set test_cases
    }
```