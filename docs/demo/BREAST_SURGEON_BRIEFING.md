# Breast panel — pre-flight briefing before the surgeon review

> **Lifecycle:** Evidence · **Audience:** reviewers preparing the breast-panel clinical review ·
> **Authority:** measured pre-flight findings and disclosed panel limitations · **Update when:** the
> champion, served breast panel or its supporting measurements change · **Generated dependencies:**
> notebook assertions and the cited shortlist artifacts · **Excludes:** general demo architecture.

Built 2026-08-19, **re-measured 2026-08-21 on champion `m7-f14`** (previously `m3-f12`). Read this
before sending `breast_shortlist.csv` to anyone clinical.

**Summary: one arm is ready, one is borderline, one has defects a surgeon will find in minutes.**
Sending all three unqualified would cost credibility we do not need to spend.

---

## 1. What was added

All twelve breast terms already sit in the model's **validation** split — honestly held out, all in
disease family 49721, so nothing here is leakage. Six were added to the persona panel, taking
`target_candidates_2` from 76,465 rows over 7 diseases to **129,253 over 13**.

The clinical trichotomy a surgeon thinks in maps onto the graph as:

| Arm | Term | Pool | Known targets | AUC (95% CI) |
|---|---|--:|--:|---|
| HR+/HER2− | luminal A breast carcinoma | 8,157 | 101 | 0.85 (0.80–0.89) |
| HER2+ | HER2 positive breast carcinoma | 12,272 | 599 | **0.94 (0.92–0.95)** |
| Triple-negative | triple-negative breast carcinoma | 2,563 | **8** | 0.89 (0.75–1.04) |
| *reference* | breast carcinoma (umbrella) | 13,290 | 864 | 0.86 (0.84–0.88) |

`hormone receptor-positive breast cancer` exists in the graph but is in no split, so **luminal A is
the HR+ proxy.** Triple-negative's CI crossing 1.0 is the Hanley–McNeil approximation breaking down
at 8 positives — read it as *"this point estimate means nothing"*, not as a good score.

---

## 2. The good news: the subtypes genuinely separate

This was the main risk. §3.4 established the model **cannot** resolve lung histological subtype —
adenocarcinoma and squamous get near-identical lists. HER2+ vs triple-negative was expected to fail
the same way.

**It does not.** Top-50 novel candidates shared: **2 of 50 (4%)** — only CDKN2B and RPA1. That
separation is stable: it was also 2/50 on the previous model, with a different second gene.

The distinction worth stating: **breast molecular subtypes are defined by markers that carry their own
curated gene associations; lung histological subtypes are defined by morphology and inherit a shared
annotation set.** So §3.4 needs narrowing — the model resolves molecularly-defined subtypes, not
morphologically-defined ones. That is a finding, not a caveat.

---

## 3. Arm-by-arm verdict

### HER2-positive — READY. Send this one.

Every gene a surgeon would check is where it should be:

| Gene | Rank | | Gene | Rank |
|---|--:|:--|---|--:|
| **ERBB2** (HER2 itself) | **14** | | EGFR | 11 |
| TP53 | **1** | | ERBB3 | 17 |
| PIK3CA | 5 | | CDK4 / CDK6 | 35 / 91 |
| AKT1 | 29 | | ESR1 | 31 |

HER2 itself at rank 14, and PI3K/AKT — the actual trastuzumab-resistance axis — at the very top. The
novel block (HRAS, NRAS, SMARCA2, IRS2, MAPK3, PTPN6, STAT5A, CRKL) is RAS/MAPK signalling downstream
of HER2. Coherent.

*Most anchors improved on the champion* — TP53 2→1, PIK3CA 7→5, EGFR 17→11, ERBB3 26→17, CDK4 53→35,
CDK6 118→91. Only AKT1 moved the wrong way (10→29).

**The one caveat to volunteer:** HER2+'s novel list overlaps `female breast carcinoma` by **35/50
(70%)**. It is an excellent *breast cancer* list; it is not strongly HER2-*specific*. Say this before
the surgeon does.

### Luminal A (HR+) — BORDERLINE.

ESR1 at rank 15 (known), PIK3CA 14, AKT1 6 — correct. AR at 25 and ERBB2 at 33 are interesting and
defensible (HER2-low is a real entity).

**But CDK4 sits at rank 174 and CDK6 at 78.** CDK4/6 inhibitors are standard of care in HR+ disease.
A surgeon will ask why. Expect that question.

### Triple-negative — DO NOT SEND UNQUALIFIED.

The pathway-level story is right, and **it got cleaner on the champion.** The top-20 novel list is
RAD50, ATM, TP53, BRCA2, NBN, BRIP1, SMAD4, SMAD3, BARD1, INHA, **ATR, MYC, EP300, RPA1, MDC1**, ESR1,
MDM2, CDK6, CTNNB1, MSH2 — with the known anchor adding CHEK2, PALB2, MRE11, BRCA1. That is the
BRCA-ness / platinum-sensitivity axis, exactly right for TNBC.

*What changed:* **PTH (parathyroid hormone) has dropped out** of the top 20, along with FGF7 and
NR2F1 — the entries an earlier draft flagged as implausible. In their place are **ATR, RPA1 and MDC1**,
all genuine DNA-damage-response. The story is tighter than it was.

**Three defects a surgeon will find immediately, and one that improved:**

1. **ESR1 at rank 17.** Triple-negative is ER-negative *by definition*. This is not a debatable call,
   it is wrong, and it is the clearest evidence that the model leaks breast-generic signal into a
   subtype defined by the *absence* of a receptor. (It was rank 14 on the previous model — marginally
   better, still indefensible.)
2. **PARP1 at rank 360.** PARP inhibition is *the* targeted therapy in TNBC. Ranking it 360 of 2,563
   while ranking its substrate pathway in the top 10 is internally inconsistent. Slightly worse than
   the 331 of the previous model.
3. **BRCA1 at rank 84 — improved from 252, and worth saying so.** It is a *known* association, and
   most BRCA1-mutant breast cancer is triple-negative, yet BRCA2 sits at rank 4. The two paralogues are
   still treated differently with no biological justification, but the gap has narrowed a great deal.
   **If the surgeon raises it, the honest answer is "we know, we improved it, it is not fixed."**
4. **TACSTD2 (TROP2) is not in the candidate pool at all** — the model cannot score it for this
   disease at any rank. Sacituzumab govitecan is approved here, and TACSTD2 is one of only *two*
   target–disease pairs the curated therapeutic label asserts for triple-negative (score 0.90). So the
   single best-evidenced TNBC target is invisible to the model. That is a coverage failure, not a
   ranking one, and TACSTD2 is a genuinely hard case — it is reachable for only **1% of all 1,157
   diseases** in the graph.

   *Corrected after measurement:* an earlier draft of this briefing also listed PDCD1/CD274
   (pembrolizumab's target) as structurally unreachable. **That was wrong** — those genes are reachable
   for 62% and 53% of diseases respectively, so their absence here is specific to triple-negative's
   known-gene set rather than a property of the graph. If the surgeon raises immunotherapy, the honest
   answer is "reachable in principle, missed for this disease", not "invisible".

Also note **TP53 at rank 2 is labelled "novel"** — but TP53 is mutated in ~80% of TNBC and appears in
the *known* block for HER2+ and for the umbrella term. So "novel" here means *"not annotated for this
particular subtype"*, not *"unknown to science"*. Explain that or the model looks naive.

---

## 4. How to run the review

`breast_shortlist.csv` — 118 rows, 4 arms. Each arm leads with its top **known** targets as a
calibration anchor, then 20 **novel** candidates. Four blank columns for the clinician:
`REVIEW_plausible_1to5`, `REVIEW_already_known_to_you`, `REVIEW_worth_pursuing`, `REVIEW_comment`.

**If the surgeon rejects the known block for an arm, stop there** — the novel block is not worth their
time, and their disagreement about the anchor is the more valuable finding.

**Suggested framing.** Lead with HER2+ to establish that the model knows breast cancer. Then use
triple-negative as the honest hard case: *"we can't score this list — 8 known associations — so your
read is the only ground truth available. Here are four things we already think are wrong with it."*
Arriving with your own list of defects is what makes the rest credible.

**Do not present the liability column as a safety verdict.** 48 of 118 rows carry the flag. It is
*enriched* for good targets, because liabilities are discovered *by* drugging something — see the
ADRB2 case in TARGET_PRIORITIZER §10.2.

---

## 5. What this changes upstream

- **PROJECT_CONTEXT §3** recommended breast cancer as a demo persona on no measurement. It now has
  one: use **HER2-positive**, not the generic `breast cancer` term, whose AUC is the panel's worst
  (0.69) — the parent term is beaten by its own children.
- **§3.4 should be narrowed** from "cannot resolve subtype" to "cannot resolve *morphological*
  subtype", with breast molecular subtypes as the counter-example.
- ⚠ **One claim has been withdrawn.** An earlier draft said triple-negative was *"the only genuinely
  subtype-specific list in the panel."* On the champion it is **not** — at 13/50 umbrella overlap it
  trails `estrogen-receptor negative` (10/50) and `estrogen-receptor positive` (11/50). It is still the
  most specific arm that has a usable number of known targets (those two have 14 and 33), and still far
  ahead of luminal A (16), luminal B (23) and HER2+ (35). **Say "among the most subtype-specific", not
  "the only one".**
- **The TNBC pool gap is real but narrow.** Measured across all 207 evaluable diseases, the candidate
  pool contains **98.5%** of curated target–disease pairs, and coverage does **not** track how sparsely
  a disease is annotated (Spearman +0.081). TNBC is one of only two diseases below 50% coverage. Do not
  present this as a systemic failure — present it as the specific reason TACSTD2 is missing here.
- **A separate and larger pool problem was found while checking this** (TARGET_PRIORITIZER §5.2.1): the
  third route in the pool filter is drug-mediated, which admits 25% of approved drug-target pairs to the
  evaluation *because of the relationship being evaluated*. Fixing it raises drug-target AUC from 0.689
  to 0.747. Not clinician-facing, but it changes numbers that are.
