# User guide

**Roles:** *admin* can upload, delete, generate/approve AI suggestions and manage users. *viewer* is read-only.

1. **Sign in.** 2. **New audit:** drop a `.cfg/.conf/.txt/.set` file (max 2 MB); vendor is auto-detected.
3. **Result page:** score ring + grade, counts, severity bar. *Findings* tab: filter by status/severity, expand a finding for the explanation, the **evidence lines** (secrets redacted), the **recommended fix** (copy button) and framework references.
4. **Status meanings:** *Fail* = evidence violates the rule; *Pass* = evidence satisfies it; *Unverified* = file lacks evidence (not counted); *N/A* = rule doesn't apply.
5. **Unrecognized commands tab:** "Suggest meanings" creates advisory suggestions; approve/reject on **AI review**. They never affect the score.
6. **Download PDF report.** 7. **History:** search/filter; tick two audits → **Compare** (improved / regressed rules).
8. **Rules library:** every rule, why it matters, fixes per vendor, references.

Score = weighted share of evaluated rules passed (critical 10, high 7, medium 4, low 2). A failed critical rule caps the grade at D.
