# JEV Behavioral & Diagnostic Analysis Log

This document tracks the cumulative behavioral fingerprint, failure mode analysis, calibration profile, and architectural hypotheses of the JEV model (`jev-latest` / `jev-1.13.0`) across stepped benchmark evaluations.

---

## 1. Executive Summary & Working Model (1,000 Decisions)

Across **1,000 evaluated decisions** (**817 / 1,000 = 81.7% overall accuracy**; Batch 3 scored **334 / 400 = 83.5%**), JEV's capability profile has solidified into four distinct behavioral tiers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        JEV 1,000-DECISION CAPABILITY SPECTRUM                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. VERY STRONG (90% – 100%)                                                            │
│    • Static propositional relationships        • Implication & contraposition          │
│    • Set / quantifier relationships            • Transitivity & ordering               │
│    • Graph reachability                        • Rule priorities & exceptions          │
│    • Source authority & stale records          • Counterexample detection              │
│    • Deterministic planning with preconditions • Preference selection                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. MODERATE (65% – 90%)                                                                │
│    • Multi-constraint assignment               • Sufficiency / inconsistency           │
│    • Belief perspectives                       • Causal intervention                   │
│    • Scheduling                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. WEAK (50% – 65%)                                                                    │
│    • Spatial updating & movement               • Truth-teller global consistency       │
│    • Token / location tracking (object swaps)                                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. EXTREMELY WEAK (< 35%)                                                              │
│    • Accumulating exact counts across evaluated propositions (33.3% All / 43.5% Core)  │
│    • Executing sequential transformations on an evolving state (13.2% All / 7.7% Core)│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

> **Central Architectural Finding**: JEV excels at evaluating a **static, structured situation** against rules, but deteriorates sharply when required to perform a computation that **repeatedly generates and replaces intermediate state** (sequential mutations) or enforces **hard cardinality equality** (exact counting). In discrete count problems, JEV behaves like a **graded evidence aggregation / compatibility maximizer** rather than a symbolic constraint checker.

---

## 2. Complete 1,000-Question Capability Profile

The table below contrasts performance across **All** items (including core questions, robustness variants, contrasts, and candidate probes) against **Core** items (the clean measure of ordinary problem solving).

| Ability / Reasoning Family | All Accuracy | Core Accuracy | Behavioral Classification |
| :--- | :---: | :---: | :--- |
| **Record lookup / filtering** | **100.0%** | **100.0%** | Very Strong (Static Relational) |
| **Forward conditional reasoning** | **100.0%** | **100.0%** | Very Strong (Static Relational) |
| **Transitive comparisons** | **100.0%** | **100.0%** | Very Strong (Static Relational) |
| **Directed reachability** | **100.0%** | **100.0%** | Very Strong (Static Relational) |
| **Source authority / stale records** | **100.0%** | **100.0%** | Very Strong (Static Relational) |
| **Boolean scope / exclusivity** | **97.7%** (43/44) | **100.0%** | Very Strong (Static Relational) |
| **Necessary conditions / contraposition** | **97.6%** | **96.6%** | Very Strong (Static Relational) |
| **Quantifiers / set relations** | **97.6%** | **100.0%** | Very Strong (Static Relational) |
| **Preference ordering** | **97.6%** | **100.0%** | Very Strong (Static Relational) |
| **Fault diagnosis** | **97.6%** | **96.0%** | Very Strong (Static Relational) |
| **Rule verification / counterexamples** | **97.7%** | **96.7%** | Very Strong (Static Relational) |
| **Temporal interval relations** | **97.0%** | **95.7%** | Very Strong (Static Relational) |
| **Planning with preconditions** | **94.1%** | **94.7%** | Very Strong (Preconditions) |
| **Exceptions / priority rules** | **91.8%** | **90.9%** | Very Strong (Static Relational) |
| **Perspective / belief tracking** | **87.8%** | **88.9%** | Moderate (Constraint) |
| **One-to-one assignments** | **84.1%** | **90.0%** | Moderate (Constraint) |
| **Causal intervention** | **80.5%** | **79.2%** | Moderate (Constraint) |
| **Sufficiency / inconsistency** | **79.4%** | **89.5%** | Moderate (Constraint) |
| **Nested reference binding** | **75.6%** | **64.3%** | Moderate (Constraint) |
| **Scheduling** | **67.3%** | **71.4%** | Moderate (Constraint) |
| **Object tracking through swaps** | **61.4%** | **62.1%** | Weak (State Tracking) |
| **Truth-teller consistency** | **59.5%** | **57.1%** | Weak (Global Constraint) |
| **Spatial tracking** | **52.5%** | **60.9%** | Weak (Spatial Updating) |
| **Exact truth counting (F09)** | **33.3%** (15/45) | **43.5%** | **Extremely Weak (Cardinality)** |
| **Sequential procedure execution (F13)** | **13.2%** (5/38) | **7.7%** (2/26) | **Extremely Weak (State Mutation)** |

---

## 3. Major Diagnostic Insights & Breakthroughs

### 1. Breakthrough: It Is NOT the Word "Exactly"
* **The Comparison**:
  * **Boolean scope / exclusivity**: **97.7% (43 / 44)** All, **100%** Core. These questions frequently require parsing rules like *"exactly one of these statements is true."*
  * **Exact truth counting (F09)**: **33.3% (15 / 45)** All, **43.5%** Core.
* **The Diagnostic Distinction**:
  * Understanding *"Exactly one of A and B"* $\to$ **Flawless**.
  * Evaluating 5–8 separate propositions, maintaining truth values, **counting them**, and requiring total $= N$ $\to$ **Catastrophic failure**.
* **Failure Mechanism**: The problem is **enumeration / cardinality accumulation**.
  * **21 of 25** wrong choices made **more statements true than required**.
  * **16 of 25** chose a candidate with the **maximum number of true statements available**.
  * **Conclusion**: JEV's Choice mechanism inherently favors candidates satisfying *more* propositions ("compatibility maximization"), overriding hard exact-count constraints.

---

### 2. Candidate Probes Disprove "Search Space Exhaustion"
Candidate probes eliminate search by supplying a candidate and asking JEV to check validity. Across 24 total probes:
* **Overall Probe Accuracy**: **11 / 24 = 45.8%**.
  * Scheduling checks: **3 / 6 (50.0%)**
  * Assignment checks: **7 / 9 (77.8%)**
  * Truth-teller checks: **1 / 4 (25.0%)**
  * Truth-counting checks: **0 / 5 (0.0%)**
* **Case Study `J000868` (Confidence 0.90)**:
  * Complete schedule is supplied; JEV is asked how many clues it violates.
  * Ground truth: violates **exactly 1** clue.
  * JEV answered: **2** (with 0.90 confidence).
  * **Takeaway**: The failure occurs **inside the evaluation of an already supplied candidate state**, linking scheduling errors directly to the cardinality accumulation defect.

---

### 3. Sequential State Execution: Stale-State Attractor
* **Accuracy**: **13.2% (5 / 38)** All, and a staggering **7.7% (2 / 26)** on Core items.
* **Intermediate State Signature**:
  * **27 of 33 errors (81.8%)** corresponded to an object that was genuinely in the queried position at an earlier point in the sequence (vs. ~19 expected by random chance).
* **Planning vs. Execution Paradox**:
  * **Planning with preconditions**: **94.1%**.
  * **Sequential execution**: **13.2%**.
  * JEV readily evaluates complex multi-step *relationships*, but cannot reliably *transform a representation through time*.

---

### 4. Object Swaps (61.4%) vs. Sequential Procedures (13.2%)
* In 8 object-swap errors, only **3** picked an earlier visited location, while **5** selected an unvisited location.
* **Takeaway**: The clean intermediate-state signature in F13 does not simply generalize to all state change tasks. There are at least three distinct sub-weaknesses:
  1. Executing arbitrary ordered list operations (F13).
  2. Binding objects to positions across swaps.
  3. Representing spatial displacement and orientation.

---

### 5. High-Confidence Forensic Case: `J001325` (First $\ge 0.95$ Error)
* **The Puzzle**:
  * Cara uses Fern.
  * Faye does not use Elm.
  * Everyone uses exactly one of Elm, Oak, Fern.
  * (Deduction: Faye must have Oak; therefore Wren must have Elm).
* **JEV's Decision**: Chose *"More than one locker remains possible"* with **0.95 confidence** (Incorrect).
* **Diagnostic Robustness**:
  * Across 4 variations, JEV chose the **identical semantic wrong answer**:
    * Long-noise version: confidence **0.83**
    * Expanded-options version: confidence **0.84**
    * Option rotation 1: confidence **0.88**
    * Option rotation 2: confidence **0.95**
  * When a controlled contrast edit made *"more than one remains possible"* genuinely true, JEV chose it correctly with **0.98** confidence.
* **New Working Hypothesis (Indirect Constraint Closure)**:
  * JEV struggles to derive uniqueness through **indirect exclusion** when the queried entity (Wren) has no direct positive or negative clue.

---

## 4. Confidence Calibration & Operational Deployment (1,000 Decisions)

Confidence remains an extraordinary predictor of decision quality:

| Confidence Threshold | Decisions Retained | Empirical Accuracy | Total Errors in Tier |
| :---: | :---: | :---: | :---: |
| **$\ge 0.50$** | 786 (78.6%) | **93.4%** | 52 |
| **$\ge 0.60$** | 734 (73.4%) | **95.5%** | 33 |
| **$\ge 0.70$** | 680 (68.0%) | **96.9%** | 21 |
| **$\ge 0.80$** | 632 (63.2%) | **97.9%** | 13 |
| **$\ge 0.90$** | 557 (55.7%) | **99.3%** | 4 |
| **$\ge 0.95$** | **493 (49.3%)** | **99.8%** | **1 (`J001325`)** |

### Operational Takeaway
Almost half of all queries (493 / 1,000) trigger confidence $\ge 0.95$, where JEV achieved **492 / 493 = 99.8% accuracy**. A selective architecture that acts autonomously when confidence $\ge 0.95$ and defers/escalates otherwise eliminates 99.5% of all runtime errors.

---

## 5. Difficulty Scaling & Positional Balance

### Difficulty Degradation
Nominal difficulty degrades gracefully, but task architecture completely dominates load:

| Difficulty Level | All Questions (1,000) | Core Questions Only |
| :---: | :---: | :---: |
| **Level 1** | **94.5%** | **95.7%** |
| **Level 2** | **85.0%** | **83.0%** |
| **Level 3** | **76.8%** | **78.7%** |
| **Level 4** | **70.2%** | **74.2%** |

### Positional Balance (Zero Slot Bias)
Across 1,000 decisions, option selection is virtually perfectly uniform (target = 200 / 20.0%):
* **Option 1**: 206 (20.6%)
* **Option 2**: 201 (20.1%)
* **Option 3**: 188 (18.8%)
* **Option 4**: 198 (19.8%)
* **Option 5**: 207 (20.7%)

---

## 6. Cumulative Evaluation Timeline & Artifacts

1. **Smoke Test (100 items)**: 100/100 valid $\to$ 88.0% accuracy.
2. **Batch 1 (300 items)**: 259 valid, 41 retries $\to$ 80.5% combined accuracy.
3. **Batch 2 (200 items)**: 200/200 valid $\to$ 80.5% batch accuracy.
4. **Batch 3 (400 items)**: 400/400 valid $\to$ 83.5% batch accuracy (28 TypeSafe failovers).
5. **Cumulative Master Files (1,000 Items)**:
   * Master CSV: [`runs/combined_400/results_completed.csv`](file:///Users/etsabary/Documents/repos/benchmarks/jev/runs/combined_400/results_completed.csv)
   * Master JSON: [`runs/combined_400/results_completed.json`](file:///Users/etsabary/Documents/repos/benchmarks/jev/runs/combined_400/results_completed.json)
   * Standalone Batch 3 CSV: [`runs/combined_400/additional_400_eval.csv`](file:///Users/etsabary/Documents/repos/benchmarks/jev/runs/combined_400/additional_400_eval.csv)
   * Compact Batch 3 CSV: [`runs/combined_400/batch_3_new_400.csv`](file:///Users/etsabary/Documents/repos/benchmarks/jev/runs/combined_400/batch_3_new_400.csv)
   * Clean Package ZIP: [`runs/combined_400/results_1000_package.zip`](file:///Users/etsabary/Documents/repos/benchmarks/jev/runs/combined_400/results_1000_package.zip)
