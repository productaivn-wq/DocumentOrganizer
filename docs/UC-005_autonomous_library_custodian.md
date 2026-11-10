# Use Case Specification: UC-005 - Autonomous Library Custodian & Discrete-Choice Auto-Filing

**Skill**: `DocumentOrganizer`  
**Standard**: IEEE 830 / BABOK v3.0  
**Status**: Approved Baseline (Approved Baseline)  
**Version**: 1.0.0  
**Source Stolen with Pride**: Extend-HQ Jevbox `server/organization.ts` and `docs/organization.md`  

---

## 1. Description & Business Objective
Enable autonomous, semantic auto-filing of loose incoming files from `Downloads/` and `00_INBOX/` into target project MECE directories using deterministic discrete-choice profile scoring for discrete choice scoring with conservative confidence thresholds ($\ge 0.65$ probability, $\ge 0.20$ margin over runner-up). Furthermore, execute an autonomous background custodian review after any successful filing: inspect up to 10 unfiled assets in `00_INBOX` and propose or execute re-filing if candidate similarity with the destination cluster reaches $\ge 0.80$.

## 2. Actors & Taxonomy
- **Primary Actor**: Agent Node ($P \in (0,1)$) initiating ingress sweeps and evaluating discrete choice candidate rankings.
- **Supporting Actor**: Code Node ($P=1$) enforcing physical file move safety, non-destructive duplicate routing (`_duplicates/`), and Unicode/Windows path safety.
- **Supervisory Actor**: Human Node (`human_operator`) approving ambiguous proposals or new root folder creations.

## 3. Preconditions
1. Source assets exist in `Downloads/`, `Desktop/`, or `00_INBOX/`.
2. Target project directories have registered descriptors in `project_router.py`.
3. Project domain profiles are loaded in `ProjectRouter`.

## 4. Main Flow (Happy Path)
1. **Intake & Extraction**: Code Node extracts document text, outline, and sample passages using `extract.py`.
2. **Deterministic Pre-Triage**: Fast keyword rules run first ($P=1$). If confidence is definitive, route directly.
3. **Discrete-Choice Discrete Choice**: For unclassified or multi-project candidates, score the document against target folder descriptors using `DiscreteChoiceScorer`.
4. **Confidence Evaluation**:
   - If top choice $\ge 0.65$ probability and leading runner-up by $\ge 0.20$: route file to target directory.
   - If below threshold: retain in `00_INBOX` or parent directory.
5. **Post-Filing Custodian Review**:
   - Inspect unfiled candidate files in `00_INBOX`.
   - Score unfiled candidates against the newly populated folder cluster.
   - If any unfiled candidate achieves $\ge 0.80$ match confidence, automatically move it to the new cluster.
6. **Provenance Sealing**: Write move and rename audit records to `move_log.md` and `log.md`.

## 5. Postconditions
- All high-confidence incoming assets are placed into project MECE zones.
- Zero original files deleted; all moves recorded in immutable logs.
