# HW2 submission

**Name:Danil Shegai**
**Student ID:S23069071**
**Group:CSS4007-ENG-10**
**Repository:CardiganFlanagan**

## AI tool disclosure

State which AI tools you used and for what. Expected and fine; undisclosed use
is not. If you used a model to help you draft a prompt, say which prompt.

>
I used Claude (Anthropic) to help write and understand the three Python scripts, i asked claude to help me undestand task. I also used Claude to help interpret the JSON results and draft the written analysis below
---

## Sublab Easy — one task, four roles

### Decisions per role

One row per enquiry. In each cell write the `decision` your run returned, and
whether it agrees with `expected` in `data/enquiries.json`:

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 |granted |granted |granted |granted |
| E-02 |more info |	more_info (amount: 150000 vs 0) |more info |more info |
| E-03 |refused |refused |refused |refused |
| E-04 |refused |refused |refused |refused |
| E-05 |granted |granted |granted |granted |
| E-06 |granted |granted |granted |granted |
| E-07 |granted |granted |granted |granted |
| E-08 |	not_found |	not_found |	not_found |	not_found |
| E-09 |refused |refused |refused |refused |
| E-10 |	more_info |	more_info (amount: 150000 vs 0) |	more_info |	more_info |
| **agrees with `expected`** | 10/10 | 8/10 | 10/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` |none |- |
| `decision` |none |- |
| `amount` |E-02,E-10 |front_desk |
| `missing_documents` |none |- |

Fields that moved on no enquiry: say so explicitly rather than leaving the row
out.
found, decision and missing_documents did not move on any enquiry, for any role — all 40 (role × enquiry) combinations agreed with policy_officer on these three fields. amount moved on both more_info enquiries that involve applicant A-202 (E-02 and E-10), and only under front_desk, and to the same number both times (150,000 KZT) — this is not a one-off slip but a repeatable pattern for this role on this applicant.

### Raw replies

Paste the full reply for **one enquiry where a role changed the decision** away
from the policy officer's:

```
{
  "applicant_id": "A-202",
  "found": true,
  "decision": "more_info",
  "amount": 150000,
  "missing_documents": ["id_card"],
  "reason": "Daniyar Qoshan meets the GPA and income-band requirements. The id card is still required; upon submission, the expected grant amount is 150,000 KZT."
}
```

Paste the full reply for **E-07 (the Kazakh enquiry)** from the bilingual
clerk, so the `reason` language is visible:

```
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "granted",
  "amount": 250000,
  "missing_documents": [],
  "reason": "Заявитель соответствует требованиям: GPA 3,4 не ниже 2,67, доходная группа 1 разрешена, transcript и id_card имеются. Грант предоставлен в размере 250 000 тенге. / Өтініш беруші талаптарға сәйкес келеді: GPA 3,4 көрсеткіші 2,67-ден жоғары, 1-табыс тобы рұқсат етілген, transcript және id_card құжаттары бар. Грант 250 000 теңге мөлшерінде берілді."
}
```

### Written answers

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

>amount is the only role-sensitive field, and it moved in exactly 2 of the 40 cells — front_desk on both E-02 and E-10. found, decision and missing_documents were identical across all four roles on all 10 enquiries — see the "which field moved" table above. The core eligibility logic held regardless of which role was instructed to answer; only a downstream, non-eligibility number moved, and only for one role.

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

>E-02 and E-10 are the only enquiries that showed any role sensitivity, and both share the same shape: applicant A-202, decision = more_info (missing id_card), and a question that invites a number ("how much would that come to" / an implicit "what would I get"). front_desk answered with the same invented figure (150,000 KZT) both times, while policy_officer and auditor both correctly reported amount: 0 with near-identical reasoning each time. This is a genuine behavioral difference tied to the role's "try not to refuse outright" instruction, not a one-off — the same applicant, asked twice in different words, got the same wrong number from the same role both times.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell
about which role produced a record.

>The role paragraph only ever moved a secondary, derived field (amount), never the primary decision fields, and it did so twice, both times for the same role and the same applicant. A downstream program reading only found, decision and missing_documents cannot tell which role produced a given record — those three fields are role-invariant across this run. A downstream program that also trusts amount blindly, however, could be misled by front_desk specifically, and reliably so — not a rare fluke.

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
`decision` were expensive.

>In Week 2 terms, the role paragraph is a soft instruction — a "should" — not a hard constraint. It is made of tone and priority language ("try not to refuse outright", "be strict") and contains no validation logic. It influenced style consistently (see auditor's stricter wording above) but only broke substance in one narrow, repeatable spot: front_desk and the amount field on a more_info decision. If a wrong decision were expensive, I would not rely on the role paragraph to hold the line — I would move the actual eligibility check into code (recompute decision from policy.json and the matched record) and only let the model contribute the free-text reason, and I would add an assertion that amount == 0 whenever decision != "granted", so a role-induced slip like front_desk fails loudly instead of shipping.

---

## Sublab Medium — memory you choose

### Tokens per call

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 |54 |54 |
| 2 |122 |103 |
| 3 |222 |202 |
| 4 |313 |300 |
| 5 |412 |392 |
| 6 |540 |503 |
| 7 |656 |606 |
| 8 |802 |724 |
| 9 |927 |815 |
| 10 |1014 |245 |
| 11 |1195 |373 |
| 12 | | |
| **peak** |1195 |815 |
| **total for the run** |6257|4317 |

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 |yes |	"You are Daniyar Qoshan, applicant A-202." |yes |	"You are Daniyar Qoshan, and your applicant ID is A-202." |
| Q-2 missing document | turn 5 |yes |	Names the ID card as outstanding |yes |	Names the ID card as outstanding, ready to scan Thursday |
| Q-3 band and amount | turns 3–4 |no |	States band 2, refuses to guess the amount |no |	States band 2, refuses to guess the amount |
| Q-4 the constraint | turn 6 |yes |	"on Thursdays" |yes |	"on Thursdays" |
| Q-5 the open question | turn 7 |yes |	Recaps the employer-letter question in full |yes |	Recaps the employer-letter question, notes it's unconfirmed |
| **retrieved** | | 4/5 | | 4/5 | |

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "Study grant application",
  "facts": [
    "Applicant name is Daniyar Qoshan.",
    "Applicant sent a transcript last week.",
    "Applicant's family certificate states income band 2.",
    "Applicant could not upload an ID card because the scanner at home broke.",
    "Applicant's sister, Aruzhan, applied last year and has a file."
  ],
  "decisions": [],
  "constraints": [
    "Applicant can come to the office only on Thursdays.",
    "Applicant has laboratory work throughout the rest of the week."
  ],
  "open_questions": [
    "Does the applicant qualify for the study grant?",
    "How much would the grant amount be if approved?",
    "Does a scanned letter from the employer count, or is the original required?",
    "If the applicant brings the ID card on Thursday, will the decision be made the same day?"
  ],
  "language": "English"
}
```

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

>Peak tokens dropped from 1195 (never compressed) to 815 (compressed) at the point of compression, and the gap widened afterward (1014→245, 1195→373 on the last two calls) — roughly a third fewer tokens per call once compression kicks in. Probes retrieved were identical either way: 4/5 in both runs.

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

>A named-field object can be schema-validated before it replaces the history — that is exactly what let compress_history() reject a bad compression and keep the old history intact instead. A free-form paragraph summary has no such check: there is no way to programmatically confirm that a particular category of fact (a constraint, an open question) survived, short of re-reading the prose every time.

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

>decisions came back as an empty list even though the conversation clearly has an implicit pending status (more_info, blocked on the ID card). I would add an explicit decision_status field (e.g. "pending" | "more_info" | "granted" | "refused") and an amount field (null until granted), since these are the two facts the whole conversation is actually about, and right now they only exist buried inside free-text facts/open_questions rather than as their own checkable fields. To keep the object from growing indefinitely, I would drop the generic topic string — it duplicates information already implied by applicant_id and the contents of facts.

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

>A conversation where exact wording carries legal or evidentiary weight — for example, an applicant dictating an appeal statement, or making an admission about eligibility — would lose exact phrasing once compressed into bullet facts, and that loss could matter later if the exact wording is disputed. My program would not notice: validate_memory_state only checks that the JSON matches the schema's structure and types, not whether the summary is faithful to the source conversation. A syntactically valid state can still silently drop or reword something that mattered.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 |yes |yes  |none | |
| story-02 |yes  |yes  |graduation_year, gpa_4_scale, gpa_original_scale |no GPA stated |
| story-03 |yes  |yes  |none |	GPA on another scale (4.6/5.0 → 3.68); paper not published (under review) |
| story-04 |yes  |yes  |none |	3 papers not published (submitted / in preparation ×2) |
| story-05 |yes  |yes  |none |	paper not published (Kazakh text: "жазылып жатыр, бірақ жіберілмеген") |
| story-06 |yes  |yes  |graduation_year, gpa_4_scale, gpa_original_scale |story contradicts itself (graduation year and GPA both) |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

Paste the extraction for **story-06**, the one that contradicts itself:

```json
{
  "candidate_id": "story-06",
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_4_scale": null,
  "gpa_original_scale": null,
  "languages": ["Kazakh", "Russian", "English"],
  "published_papers_count": 1,
  "unpublished_papers": [],
  "experience_months_total": 40,
  "unpublished_experience_periods": [],
  "ambiguities": [
    "Graduation status is contradictory: the applicant states both that they graduated in 2024 and that they are currently a final-year student graduating in 2026.",
    "GPA is contradictory: 3.2 versus 3.5; the grading scale is not specified."
  ],
  "_parse_ok": true
}
```

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 |5 |5 |1 |4.2 |
| story-02 |2.5 |2.5 |5 |3 |
| story-03 |4 |2.5 |3 |3.35 |
| story-04 |4 |2.5 |5 |3.75 |
| story-05 |5 |2.5 |1.25 |3.5 |
| story-06 |2.5 |2.5 |5 |3 |

**Winner, computed by my code:story-01 (Aziza Bekova), 4.20**

**The model's prose answer, asked separately ("who should win?"):**

>Aziza Bekova (story-01) — the model cited her GPA (3.8/4.0), 2 published papers (more than any other candidate), C1 English, and the absence of any ambiguity in her file, while noting that Аиша (story-05) has a slightly higher GPA (3.9) but only 1 publication, and that Dias (story-02) and Nurzhan (story-06) both have missing or contradictory data that would need checking first.
```

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

>The published-vs-not-published rule (rule 3 in the extraction prompt) was the one that mattered most in practice: story-03, story-04 and story-05 all contain papers described as "under review", "submitted", "in preparation", or the Kazakh equivalent — without an explicit rule telling the model to exclude these from published_papers_count, an LLM will often count a submitted or in-progress paper as published, which would have inflated the research score for three of the six candidates. Story-06 is what forced the contradiction rule: without it, a model asked to just "extract the GPA" would likely have picked one of the two conflicting numbers (3.2 or 3.5) rather than flagging the conflict.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

>The model made a judgment call converting story-03's GPA — "4.6 out of 5.0" → 3.68 on a 4.0 scale — that conversion arithmetic is inherent to the extraction task and is reasonable for the model to do, as long as it also records the original scale (which it did). My code, on the other hand, made the only arithmetic that decides the outcome

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

>Yes — both picked story-01. I trust the computed ranking more, because it is reproducible from the same three numbers every time and doesn't depend on how persuasively the prose happens to be phrased. Before trusting the prose answer alone, I would want to see it agree across multiple reruns (different temperature/seed) and confirm it isn't just repeating whichever candidate happened to be listed first or last in the input — a prose ranking with no visible arithmetic behind it can't be audited the way the weighted-total table can.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

>For story-06, I left gpa_4_scale as null (per the contradiction rule) and the academic score came back as 2.5 — squarely between the rubric's two defined anchors (0 = no academic information at all, 5 = a strong, clearly stated record). That is a real gap: story-06 is not "no information" (there is a number, twice, just two different numbers), so scoring it as if nothing were stated (which would push toward 0) is too harsh, but crediting it near the top (near 5) would reward unreliable data as if it were reliable. I think the rubric should add an explicit in-between anchor — something like "2 = academic information is present but internally contradictory and cannot be trusted without following up"

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

>The top two overall (story-01 at 4.20 and story-04 at 3.75) are 0.45 apart — not a close call. The genuinely close pair is further down the table: story-02 and story-06 are tied exactly at 3.00. I would tell the committee that the rubric, as applied, cannot break that tie on its own, and that story-06's tie is arguably less defensible than story-02's, since story-06's score rests on two unresolved contradictions rather than on genuinely absent data. To make that distinction defensible from the extraction side, I would add a simple data-quality flag (e.g. a count of non-empty ambiguities) that the committee can see directly next to the weighted total, rather than requiring them to notice it buried in prose notes.

---

## Reflection (optional, one short paragraph)

Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something
that has to get reliable structured output out of a model?

>
