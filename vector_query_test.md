# Comprehensive Vector Search Verification Audit Logs

### Result Log Output Evidence
```text
==================================================
[AUDIT] Chroma DB Collection Verification
 -> Targeted Collection:   coverage_kb
 -> Current collection.count(): 136
==================================================
[SUCCESS] Verification Passed! The database index size matches your chunk count perfectly.
==================================================
```
* **Audit Determination**: Ingestion pipeline status is **100% Complete**. All 136 chunks (both structured spreadsheet rows and sentence-safe text sections) are accounted for on disk.

**Target Core Query:** `Is physical therapy covered under the Silver plan?`

## 1. Unfiltered Baseline Query (Top 5 Matches)
Matches across all available indexed document source types without restrictions.

| Rank | Score | Source File | Section / Plan Type | Document Text Content |
| :--- | :--- | :--- | :--- | :--- |
| #1 | 0.6795 | benefits.txt | EXCLUSIONS / PPO/HMO Mixed | (referred to in this document as the “Silver plan”) and Gold Plan. It doesn’t include everything about what’s covered and not covered or all the plan rules. For details, see the Evidence of Coverage (EOC), which is located on our website at kp.org/eocco or ask for a copy from Member Services by calling 1-800-476-2167 (TTY 711), 7 days a week, 8 a.m. to 8 p.m. Kaiser Permanente Senior Advantage Bronze, Silver and Gold plans have a Point-of-Service (POS) |
| #2 | 0.7777 | benefits.txt | COVERAGE / PPO/HMO Mixed | --- Page 5 --- Benefits and premiums With our Bronze With our Core With our Silver With our Gold Plan, you pay Plan, you pay Plan, you pay Plan, you pay • Cardiovascular disease covered covered covered covered (behavioral therapy) services. services. services. services. • Cervical & vaginal cancer screenings • Colorectal cancer screenings Blood-based o biomarker tests Colonoscopies o Computed o tomography (CT) colonography Fecal occult blood o tests Flexible o sigmoidoscopies |
| #3 | 0.8313 | benefits.txt | COVERAGE / PPO/HMO Mixed | Silver plan members. • $10 per individual therapy visit and $5 per group therapy visit for mental health, psychiatric and substance abuse care for Bronze plan members, and $5 per individual therapy visit and $0 per group therapy visit for mental health, psychiatric and substance abuse care for Silver or Gold plan members. • $5 per visit for pulmonary rehabilitation. • $0 for primary care visits. • $0 for lab tests, and diagnostic tests. • $0 per X-ray. • $0 for preventive care visits. |
| #4 | 0.8677 | benefits.txt | COVERAGE / PPO/HMO Mixed | members, $15 per specialty care visit for Silver benefit maximum of $1,000 in covered plan or Gold plan members. charges per calendar year. • $35 per individual specialty care visit and $0 per Covered services, include, but are not limited to: group visit for cardiac rehabilitation and • Preventive services covered at $0 under intensive cardiac rehabilitation for Bronze plan Original Medicare. members, $15 per individual specialty care visit |
| #5 | 0.9206 | benefits.txt | COVERAGE / PPO/HMO Mixed | --- Page 17 --- These benefits are available to you as a plan You pay member: • $35 per podiatry visit for Bronze plan members, $15 per podiatry visit for Silver or Gold plan members. • $25 per visit for physical, speech, and occupational therapy for Bronze plan members and $10 per visit for physical, speech, and occupational therapy for Silver or Gold plan members. • $15 per chiropractic visit for Bronze or Gold plan members, and $20 per chiropractic visits for Silver plan members. |

================================================================================

## 2. Metadata-Filtered Query (Scope Constraint: `plan_type == HMO`)
Verification Check: All rows must match the plan_type criteria context window explicitly.

| Rank | Score | Source File | Section / Plan Type | Document Text Content |
| :--- | :--- | :--- | :--- | :--- |
| #1 | 1.1164 | plans.csv | COVERAGE / HMO | Silver HMO: $300/month premium, $1500 deductible, 20% coinsurance, network: silver |
| #2 | 1.2306 | plans.csv | COVERAGE / HMO | Bronze HMO: $150/month premium, $1000 deductible, 30% coinsurance, network: bronze |
