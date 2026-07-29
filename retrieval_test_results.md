# Hybrid Retrieval Routing Engine Test Audit Report

**Verification Execution Timestamp:** `2026-07-29T02:20:37Z`
**Active Chroma Storage Node:** `/Users/ada/myprojects/my-first-app/chroma_db`

### Test Case #1
**Question:** What is my annual deductible under the Gold PPO plan?

**Classification:** `STRUCTURED`

**Retrieved Context:**
```text
--- STRUCTURED PLAN METRICS (DATABASE LOOKUP) ---
Plan: Gold PPO | Monthly Premium: $500 | Annual Deductible: $2000 | Copay Coinsurance: 10% | Tier Group: GOLD
```
**Manual Score:** `Good`
-------------------------------------------------------------------------------------

### Test Case #2
**Question:** Is physical therapy covered by my insurance policy?

**Classification:** `UNSTRUCTURED`

**Retrieved Context:**
```text
--- UNSTRUCTURED POLICY DOCUMENT SECTIONS (VECTOR LOOKUP) ---
[Ref #1 | Source: benefits.txt | Section: EXCLUSIONS]
Note: You pay the same plan copays and coinsurance when you get covered care listed above from
non-plan providers. If you receive non-covered care or services, you must pay the full cost.
For details about coverage rules, including non-covered services (exclusions), see the
Evidence of Coverage.
Getting care
At most of our plan facilities, you can usually get all the covered services you need, including specialty

[Ref #2 | Source: benefits.txt | Section: COVERAGE]
• Alcohol misuse services services services services
approved by approved by approved by approved by
screenings & counseling
Medicare during Medicare during Medicare during Medicare during
• Bone mass
the contract year the contract year the contract year the contract year
measurements
will be covered. will be covered. will be covered. will be covered.
• Cardiovascular disease
See your EOC See your EOC See your EOC See your EOC
screenings

[Ref #3 | Source: benefits.txt | Section: EXCLUSIONS]
--- Page 16 ---
These benefits are available to you as a plan You pay
member:
www.YourOnePass.com or call 1-877-614-0618
(TTY 711), Monday through Friday, 7 a.m. to 8
p.m.
Home medical care not covered by Medicare $0 when prescribed as part of your home
(Advanced Care at Home)*† treatment plan, otherwise you pay the applicable
We cover medical care in your home that is not cost share
otherwise covered by Medicare when found
medically appropriate by a physician based on

[Ref #4 | Source: benefits.txt | Section: COVERAGE]
days 51–100 days 40–100 days 36–100
Physical therapy* $25 per visit $10 per visit $10 per visit $10 per visit
Ambulance† $350 per one- $325 per one- $300 per one- $250 per one-
way trip way trip way trip way trip
Transportation $0 for up to 18 $0 for up to 12 $0 for up to 26 $0 for up to 40
We cover a certain amount one-way trips one-way trips one-way trips one-way trips
of one-way trips per per calendar per calendar per calendar per calendar

[Ref #5 | Source: benefits.txt | Section: COVERAGE]
standards.
• You get all covered services and items from plan providers listed in our Provider Directory and
Pharmacy Directory. But there are exceptions to this rule. We also cover:
Care from plan providers in another Kaiser Permanente Region
o
For Bronze, Silver, and Gold plan members only, care covered under the Medicare Explorer point-
o
of-service benefit. See the Evidence of Coverage for details.
Emergency care
o
Out-of-area dialysis care
o
```
**Manual Score:** `Partial`
-------------------------------------------------------------------------------------

### Test Case #3
**Question:** Show me the monthly premium costs for all available plans.

**Classification:** `STRUCTURED`

**Retrieved Context:**
```text
--- STRUCTURED PLAN METRICS (DATABASE LOOKUP) ---
Plan: Gold PPO | Monthly Premium: $500 | Annual Deductible: $2000 | Copay Coinsurance: 10% | Tier Group: GOLD
Plan: Silver HMO | Monthly Premium: $300 | Annual Deductible: $1500 | Copay Coinsurance: 20% | Tier Group: SILVER
Plan: Bronze HMO | Monthly Premium: $150 | Annual Deductible: $1000 | Copay Coinsurance: 30% | Tier Group: BRONZE
```
**Manual Score:** `Good`
-------------------------------------------------------------------------------------

### Test Case #4
**Question:** Are cosmetic surgeries listed as exclusions under the Silver tier?

**Classification:** `UNSTRUCTURED`

**Retrieved Context:**
```text
--- UNSTRUCTURED POLICY DOCUMENT SECTIONS (VECTOR LOOKUP) ---
[Ref #1 | Source: benefits.txt | Section: COVERAGE]
--- Page 5 ---
Benefits and premiums With our Bronze With our Core With our Silver With our Gold
Plan, you pay Plan, you pay Plan, you pay Plan, you pay
• Cardiovascular disease covered covered covered covered
(behavioral therapy) services. services. services. services.
• Cervical & vaginal
cancer screenings
• Colorectal cancer
screenings
Blood-based
o
biomarker tests
Colonoscopies
o
Computed
o
tomography (CT)
colonography
Fecal occult blood
o
tests
Flexible
o
sigmoidoscopies

[Ref #2 | Source: benefits.txt | Section: EXCLUSIONS]
(referred to in this document as the “Silver plan”) and Gold Plan. It doesn’t include everything about what’s
covered and not covered or all the plan rules. For details, see the Evidence of Coverage (EOC), which is
located on our website at kp.org/eocco or ask for a copy from Member Services by calling
1-800-476-2167 (TTY 711), 7 days a week, 8 a.m. to 8 p.m.
Kaiser Permanente Senior Advantage Bronze, Silver and Gold plans have a Point-of-Service (POS)

[Ref #3 | Source: benefits.txt | Section: COVERAGE]
--- Page 14 ---
Advantage Plus Option 1 With our Bronze With our Core With our Silver With our Gold
benefits and premium Plan, you pay Plan, you pay Plan, you pay Plan, you pay
“Dental services” above. Premier® Premier® Premier® Premier®
The benefit limits combine, dentists, you pay dentists, you pay dentists, you pay dentists, you pay
as shown on the right. 100% for the rest 100% for the rest 100% for the rest 100% for the rest
A summary of of the year. of the year. of the year. of the year.

[Ref #4 | Source: benefits.txt | Section: COVERAGE]
members, $15 per specialty care visit for Silver
benefit maximum of $1,000 in covered plan
or Gold plan members.
charges per calendar year.
• $35 per individual specialty care visit and $0 per
Covered services, include, but are not limited to:
group visit for cardiac rehabilitation and
• Preventive services covered at $0 under intensive cardiac rehabilitation for Bronze plan
Original Medicare.
members, $15 per individual specialty care visit

[Ref #5 | Source: plans.csv | Section: COVERAGE]
Silver HMO: $300/month premium, $1500 deductible, 20% coinsurance, network: silver
```
**Manual Score:** `Poor`
-------------------------------------------------------------------------------------

### Test Case #5
**Question:** What is the copay percentage for the Bronze HMO choice?

**Classification:** `UNSTRUCTURED`

**Retrieved Context:**
```text
--- UNSTRUCTURED POLICY DOCUMENT SECTIONS (VECTOR LOOKUP) ---
[Ref #1 | Source: plans.csv | Section: COVERAGE]
Bronze HMO: $150/month premium, $1000 deductible, 30% coinsurance, network: bronze

[Ref #2 | Source: plans.csv | Section: COVERAGE]
Silver HMO: $300/month premium, $1500 deductible, 20% coinsurance, network: silver

[Ref #3 | Source: benefits.txt | Section: COVERAGE]
--- Page 9 ---
Benefits and premiums With our Bronze With our Core With our Silver With our Gold
Plan, you pay Plan, you pay Plan, you pay Plan, you pay
We cover up to 100 days • $0 per day for • $0 per day for • $0 per day for • $0 per day for
per benefit period. days 1–20 days 1–20 days 1–20 days 1–10
• $203 per day • $203 per day • $203 per day • $20 per day
for days 21– for days 21– for days 21– for days 11–
50 39 35 100
• $0 per day for • $0 per day for • $0 per day for

[Ref #4 | Source: benefits.txt | Section: COVERAGE]
--- Page 15 ---
Advantage Plus Option 2 With our Bronze With our Core With our Silver With our Gold
benefits and premium Plan, you pay Plan, you pay Plan, you pay Plan, you pay
provided by our give you 38 one- give you 32 one- give you 46 one- give you 60 one-
transportation provider. way trips per way trips per way trips per way trips per
For more information, visit calendar year. calendar year. calendar year. calendar year.
kp.org/seniorhealth/extra
s.
In-home-support $0 $0 $0 $0

[Ref #5 | Source: benefits.txt | Section: COVERAGE]
limit. limit. limit. limit.
Advantage Plus Option 2 With our Bronze With our Core With our Silver With our Gold
benefits and premium Plan, you pay Plan, you pay Plan, you pay Plan, you pay
Additional monthly $20 $20 $20 $20
premium
Acupuncture $15 per visit $15 per visit $15 per visit $15 per visit
16 visits per calendar year
Hearing aids* A $500 allowance A $500 allowance A $500 allowance A $500 allowance
$500 allowance to buy 1 is added to the is added to the is added to the is added to the
```
**Manual Score:** `Partial`
-------------------------------------------------------------------------------------

### Test Case #6
**Question:** How do I file a medical claim or get an update on billing error codes?

**Classification:** `UNSTRUCTURED`

**Retrieved Context:**
```text
--- UNSTRUCTURED POLICY DOCUMENT SECTIONS (VECTOR LOOKUP) ---
[Ref #1 | Source: claims_process.txt | Section: CLAIMS]
--- Table Data ---
Error Code | Root Cause Description | Immediate Action Required
ERR-102 | Missing or invalid member ID number | Reject claim; return to sender for identity verification.
ERR-305 | No prior authorization on file | Forward to the medical necessity review board for retrospective audit.
ERR-501 | Duplicate billing detected | Deny line item; cross-reference with the previously paid historical claim ID.

[Ref #2 | Source: benefits.txt | Section: CLAIMS]
money or lower your drug costs. Contact us or visit medicare.gov to learn more about this program.
Notices
Appeals and grievances
You can ask us to provide or pay for an item or service you think should be covered by submitting a claim
to us within a specific time period that includes the date you received the item or service. If we say no, you
can ask us to reconsider our decision. This is called an appeal. You can ask for a fast decision if you think

[Ref #3 | Source: claims_process.txt | Section: CLAIMS]
Step 2: Member and Provider Verification
Match the patient’s Member ID, group number, and date of birth against the active enrollment registry.
Cross-reference the billing provider's National Provider Identifier (NPI) to confirm network participation status.
Step 3: Medical Adjudication
Validate that all diagnostic codes (ICD-10-CM) align logically with the billed procedure codes (CPT/HCPCS).

[Ref #4 | Source: benefits.txt | Section: COVERAGE]
Office for Civil Rights electronically through the Office for Civil Rights Complaint Portal, available at
https://ocrportal.hhs.gov/ocr/portal/lobby.jsf, or by mail or phone at: U.S. Department of Health and
Human Services, 200 Independence Avenue SW., Room 509F, HHH Building, Washington, DC
20201, 1-800-368-1019, (TTY 1-800-537-7697). Complaint forms are available at
hhs.gov/ocr/office/file/index.html.
This notice is available at
https://healthy.kaiserpermanente.org/colorado/language-

[Ref #5 | Source: claims_process.txt | Section: EXCLUSIONS]
Review the patient's plan files to calculate deductible tracking, co-insurance percentages, and out-of-pocket maximums. [1]
Step 4: Final Settlement & Notification
Generate the final payment or issue a formal denial notice within 30 business days of initial receipt.
Distribute the Explanation of Benefits (EOB) statement directly to the member.
3. Claim Auditor Checklist
The processing agent must verify and check off each item before finalizing adjudication:
```
**Manual Score:** `Good`
-------------------------------------------------------------------------------------

### Test Case #7
**Question:** What are the premium and deductible costs for the Silver HMO plan?

**Classification:** `STRUCTURED`

**Retrieved Context:**
```text
--- STRUCTURED PLAN METRICS (DATABASE LOOKUP) ---
Plan: Silver HMO | Monthly Premium: $300 | Annual Deductible: $1500 | Copay Coinsurance: 20% | Tier Group: SILVER
```
**Manual Score:** `Good`
-------------------------------------------------------------------------------------

### Test Case #8
**Question:** Is outpatient speech evaluation covered under the Silver plan?

**Classification:** `BOTH`

**Retrieved Context:**
```text
--- STRUCTURED PLAN METRICS (DATABASE LOOKUP) ---
Plan: Silver HMO | Monthly Premium: $300 | Annual Deductible: $1500 | Copay Coinsurance: 20% | Tier Group: SILVER

--- UNSTRUCTURED POLICY DOCUMENT SECTIONS (VECTOR LOOKUP) ---
[Ref #1 | Source: benefits.txt | Section: EXCLUSIONS]
(referred to in this document as the “Silver plan”) and Gold Plan. It doesn’t include everything about what’s
covered and not covered or all the plan rules. For details, see the Evidence of Coverage (EOC), which is
located on our website at kp.org/eocco or ask for a copy from Member Services by calling
1-800-476-2167 (TTY 711), 7 days a week, 8 a.m. to 8 p.m.
Kaiser Permanente Senior Advantage Bronze, Silver and Gold plans have a Point-of-Service (POS)

[Ref #2 | Source: benefits.txt | Section: COVERAGE]
--- Page 5 ---
Benefits and premiums With our Bronze With our Core With our Silver With our Gold
Plan, you pay Plan, you pay Plan, you pay Plan, you pay
• Cardiovascular disease covered covered covered covered
(behavioral therapy) services. services. services. services.
• Cervical & vaginal
cancer screenings
• Colorectal cancer
screenings
Blood-based
o
biomarker tests
Colonoscopies
o
Computed
o
tomography (CT)
colonography
Fecal occult blood
o
tests
Flexible
o
sigmoidoscopies

[Ref #3 | Source: benefits.txt | Section: COVERAGE]
Silver plan members.
• $10 per individual therapy visit and $5 per group
therapy visit for mental health, psychiatric and
substance abuse care for Bronze plan
members, and $5 per individual therapy visit
and $0 per group therapy visit for mental health,
psychiatric and substance abuse care for Silver
or Gold plan members.
• $5 per visit for pulmonary rehabilitation.
• $0 for primary care visits.
• $0 for lab tests, and diagnostic tests.
• $0 per X-ray.
• $0 for preventive care visits.

[Ref #4 | Source: benefits.txt | Section: COVERAGE]
service area, please see Chapter 4, Section 2.2, in care visit for other healthcare professionals for
the Evidence of Coverage. Bronze plan members, $15 per specialty care
visit and $0 per primary care visit for other
healthcare professionals for Silver or Gold plan
members.
• $35 per opioid treatment program services visit
for Bronze plan members, $15 per opioid
treatment program services for Silver or Gold
plan members.
14

[Ref #5 | Source: benefits.txt | Section: COVERAGE]
members, $15 per specialty care visit for Silver
benefit maximum of $1,000 in covered plan
or Gold plan members.
charges per calendar year.
• $35 per individual specialty care visit and $0 per
Covered services, include, but are not limited to:
group visit for cardiac rehabilitation and
• Preventive services covered at $0 under intensive cardiac rehabilitation for Bronze plan
Original Medicare.
members, $15 per individual specialty care visit
```
**Manual Score:** `Partial`
-------------------------------------------------------------------------------------

### Test Case #9
**Question:** Does the Bronze plan have a higher monthly cost than the Gold plan?

**Classification:** `STRUCTURED`

**Retrieved Context:**
```text
--- STRUCTURED PLAN METRICS (DATABASE LOOKUP) ---
Plan: Gold PPO | Monthly Premium: $500 | Annual Deductible: $2000 | Copay Coinsurance: 10% | Tier Group: GOLD
```
**Manual Score:** `Partial`
-------------------------------------------------------------------------------------

### Test Case #10
**Question:** Are experimental clinical drug trials completely restricted or denied?

**Classification:** `UNSTRUCTURED`

**Retrieved Context:**
```text
--- UNSTRUCTURED POLICY DOCUMENT SECTIONS (VECTOR LOOKUP) ---
[Ref #1 | Source: benefits.txt | Section: COVERAGE]
copays, which are referred to in this document as standard pharmacies.
Prior authorization
Some services or items are covered only if your plan provider gets approval in advance from our
plan (sometimes called prior authorization). Services or items subject to prior authorization are
flagged with a † symbol in this document.
Region
A Kaiser Foundation Health Plan organization. We have Kaiser Permanente Regions located in

[Ref #2 | Source: benefits.txt | Section: COVERAGE]
supply isn’t available for all drugs.
• The type of plan pharmacy that fills your prescription (preferred pharmacy, standard pharmacy, or our
mail-order pharmacy). To find our pharmacy locations, see the Pharmacy Directory at
kp.org/directory. Note: Not all drugs can be mailed.
• The coverage stage you’re in (deductible, initial coverage or catastrophic coverage stages).
Note: Medicare provides Extra Help to pay prescription drug costs for people who have limited income

[Ref #3 | Source: benefits.txt | Section: COVERAGE]
and the Pharmacy less than 20% if less than 20% if less than 20% if less than 20% if
Directory for preferred and those drugs are those drugs are those drugs are those drugs are
standard plan pharmacy determined to determined to determined to determined to
locations. exceed the exceed the exceed the exceed the
amount of amount of amount of amount of
• Drugs that must be
inflation. inflation. inflation. inflation.
administered by a health
care professional

[Ref #4 | Source: benefits.txt | Section: CLAIMS]
money or lower your drug costs. Contact us or visit medicare.gov to learn more about this program.
Notices
Appeals and grievances
You can ask us to provide or pay for an item or service you think should be covered by submitting a claim
to us within a specific time period that includes the date you received the item or service. If we say no, you
can ask us to reconsider our decision. This is called an appeal. You can ask for a fast decision if you think

[Ref #5 | Source: benefits.txt | Section: ENROLLMENT]
and resources. If you are entitled to Extra Help, the cost-sharing below may not apply to you; instead,
please refer to the Evidence of Coverage Rider for People Who Get Extra Help Paying for
Prescription Drugs.
8
```
**Manual Score:** `Poor`
-------------------------------------------------------------------------------------

