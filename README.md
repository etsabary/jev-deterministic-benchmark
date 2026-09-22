# JEV Deterministic Decision Benchmark

I wanted to understand what kinds of decisions Jev actually makes well.

I tested `jev-latest` (snapshot `jev-1.13.0`) on 1,000 deterministic decisions across 25 reasoning families on the `JEV-DD-1.0` benchmark. The overall accuracy was 81.7%, but the average hides a much more interesting pattern.

---

## The short version

Jev is extremely strong when it can evaluate a relatively static situation against clear rules.

It scored around 97–100% on tasks involving:
- conditional reasoning
- contraposition
- quantifiers and set relations
- transitive comparisons
- directed reachability
- source authority
- counterexample detection
- preference ordering

It performed much less reliably when the task required repeatedly changing an internal state or explicitly accumulating exact counts.

Two results stood out:

* **Sequential procedure execution: 13.2%**  
  When Jev was wrong, 81.8% of its errors selected something that really had been correct at an earlier point in the sequence.
* **Exact truth counting: 33.3%**  
  In 84% of the analyzed errors, Jev chose an option satisfying more statements than the required exact number. This suggests that in these cases it may be treating the task more like graded compatibility than strict counting.

Its confidence signal was also unusually informative. Of 493 decisions with reported confidence of 0.95 or higher, 492 were correct.

---

## What this suggests

The clearest distinction I found is between evaluating a static structured situation and executing a sequence of state changes.

Jev can handle some surprisingly sophisticated logical relationships very well. Difficulty rises sharply when the task requires it to repeatedly update a representation, keep intermediate states separate, or count several evaluated conditions exactly.

These are behavioural findings. They describe what Jev did on this benchmark, not the internal mechanism producing those decisions.

👉 **[Explore the interactive dashboard](https://etsabary.github.io/jev-deterministic-benchmark/)**

The full questions, results, benchmark runner, charts, and analysis are in this repository.

---

## Results across 25 reasoning families

The table below contrasts performance across **All** items (including core questions, robustness variants, contrasts, and candidate probes) against **Core** items (ordinary single-step problems).

| Reasoning Family | All Accuracy | Core Accuracy | Category |
| :--- | :---: | :---: | :--- |
| **Record lookup / filtering** | **100.0%** | **100.0%** | Static Relational |
| **Forward conditional reasoning** | **100.0%** | **100.0%** | Static Relational |
| **Transitive comparisons** | **100.0%** | **100.0%** | Static Relational |
| **Directed reachability** | **100.0%** | **100.0%** | Static Relational |
| **Source authority / stale records** | **100.0%** | **100.0%** | Static Relational |
| **Boolean scope / exclusivity** | **97.7%** (43/44) | **100.0%** | Static Relational |
| **Necessary conditions / contraposition** | **97.6%** | **96.6%** | Static Relational |
| **Quantifiers / set relations** | **97.6%** | **100.0%** | Static Relational |
| **Preference ordering** | **97.6%** | **100.0%** | Static Relational |
| **Fault diagnosis** | **97.6%** | **96.0%** | Static Relational |
| **Rule verification / counterexamples** | **97.7%** | **96.7%** | Static Relational |
| **Temporal interval relations** | **97.0%** | **95.7%** | Static Relational |
| **Planning with preconditions** | **94.1%** | **94.7%** | Preconditions |
| **Exceptions / priority rules** | **91.8%** | **90.9%** | Static Relational |
| **Perspective / belief tracking** | **87.8%** | **88.9%** | Constraints |
| **One-to-one assignments** | **84.1%** | **90.0%** | Constraints |
| **Causal intervention** | **80.5%** | **79.2%** | Constraints |
| **Sufficiency / inconsistency** | **79.4%** | **89.5%** | Constraints |
| **Nested reference binding** | **75.6%** | **64.3%** | Constraints |
| **Scheduling** | **67.3%** | **71.4%** | Constraints |
| **Object tracking through swaps** | **61.4%** | **62.1%** | State Tracking |
| **Truth-teller consistency** | **59.5%** | **57.1%** | Global Constraints |
| **Spatial tracking** | **52.5%** | **60.9%** | Spatial Updating |
| **Exact truth counting (F09)** | **33.3%** (15/45) | **43.5%** | Cardinality Accumulation |
| **Sequential procedure execution (F13)** | **13.2%** (5/38) | **7.7%** (2/26) | State Mutation |

---

## Visual summary

### 1. Capability Spectrum (All vs. Core)
![Reasoning Families Capability Spectrum](charts/reasoning_families_accuracy.svg)

### 2. Confidence Calibration Curve
![Confidence Calibration Profile](charts/confidence_calibration.svg)

### 3. Error Patterns in Sequential Execution and Exact Counting
![Anatomy of Failure Modes](charts/failure_modes_f09_f13.svg)

---

## Two concrete examples of what fails

The full analysis log ([`DIAGNOSTIC_ANALYSIS.md`](DIAGNOSTIC_ANALYSIS.md)) documents multiple failure cases in detail. Here are two illustrative examples:

### 1. Sequential procedure execution (`J001646`)
* **Observed error pattern:** Selection of earlier intermediate states.

> **Context:** Five name cards start in this left-to-right order: `Pia, Noel, Zane, Gus, Quin`. Carry out the numbered steps in numerical order. Positions always refer to the current order, not the initial order.
> 
> * Step 1: Reverse the whole left-to-right order.
> * Step 2: Reverse the whole left-to-right order.
> * Step 3: Reverse the whole left-to-right order.
> * Step 4: Move the last card to the first position, keeping the order of the others.
> * Step 5: Move the last card to the first position, keeping the order of the others.
> * Step 6: Swap the first and last cards; leave the others in place.
> 
> **Question:** Which name is in the fifth position at the end?  
> Options: `(1) Zane`, `(2) Pia`, `(3) Quin`, `(4) Gus`, `(5) Noel`

* **What happens step-by-step:**
  1. Initial: `[Pia, Noel, Zane, Gus, Quin]`
  2. Step 1: `[Quin, Gus, Zane, Noel, Pia]`
  3. Step 2: `[Pia, Noel, Zane, Gus, Quin]`
  4. Step 3: `[Quin, Gus, Zane, Noel, Pia]` *(Pia is in position 5 here)*
  5. Step 4: `[Pia, Quin, Gus, Zane, Noel]`
  6. Step 5: `[Noel, Pia, Quin, Gus, Zane]`
  7. Step 6: `[Zane, Pia, Quin, Gus, Noel]` $\to$ **Correct Answer is Noel (Option 5)**.

* **Gold Option:** **Option 5 (Noel)**
* **Jev's Choice:** **Option 2 (Pia)**
* **Observation:** Jev selected **Pia**, which occupied the queried position at **Step 3**. Across 33 analyzed sequential errors, **81.8% (27/33)** chose an object that genuinely occupied the queried slot at an earlier point in the sequence.

---

### 2. Exact truth counting (`J001161`)
* **Observed error pattern:** Preference for candidates satisfying more conditions.

> **Context:** A prize is in exactly one of five chests: `Hazel, Pine, Cedar, Oak and Laurel`. Exactly three of the numbered inscriptions below are true.
> 
> * Inscription 1: The prize is not in the Pine chest.
> * Inscription 2: The prize is in neither the Pine chest nor the Cedar chest.
> * Inscription 3: The prize is in the Laurel chest.
> * Inscription 4: The prize is in the Hazel chest or the Pine chest.
> * Inscription 5: The prize is in neither the Cedar chest nor the Laurel chest.
> * Inscription 6: The prize is in neither the Hazel chest nor the Pine chest.
> * Inscription 7: The prize is in neither the Hazel chest nor the Oak chest.
> * Inscription 8: The prize is not in the Cedar chest.
> 
> **Question:** Which chest contains the prize?  
> Options: `(1) Oak chest`, `(2) Cedar chest`, `(3) Laurel chest`, `(4) Hazel chest`, `(5) Pine chest`

* **Truth-value check:**
  * **Cedar (Option 2, Correct):** Inscriptions 1, 6, 7 are True $\to$ **exactly 3 true statements**.
  * **Oak (Option 1, Jev's choice):** Inscriptions 1, 2, 5, 6, 8 are True $\to$ **5 true statements**.

* **Gold Option:** **Option 2 (Cedar chest)**
* **Jev's Choice:** **Option 1 (Oak chest)**
* **Observation:** Oak satisfies **5 true statements** instead of the required 3. Across all 25 analyzed F09 errors, **84.0% (21/25)** chose candidates with *more* true statements than required, and **64.0% (16/25)** chose the candidate with the *maximum* possible true statements.
* **Important distinction:** Jev scored **97.7%** on Boolean scope problems that use phrases like *"exactly one is true."* This suggests the difficulty is not understanding the word *"exactly,"* but rather accumulating and checking exact cardinality counts across multiple evaluated propositions.

*(Additional failure cases involving spatial movement, orientation anchoring, and candidate probes are detailed in [`DIAGNOSTIC_ANALYSIS.md`](DIAGNOSTIC_ANALYSIS.md)).*

---

## Confidence calibration

Across the 1,000 decisions, Jev's reported confidence was remarkably predictive:

| Confidence Threshold | Decisions Retained | Empirical Accuracy | Errors |
| :---: | :---: | :---: | :---: |
| **$\ge 0.50$** | 786 (78.6%) | **93.4%** | 52 |
| **$\ge 0.60$** | 734 (73.4%) | **95.5%** | 33 |
| **$\ge 0.70$** | 680 (68.0%) | **96.9%** | 21 |
| **$\ge 0.80$** | 632 (63.2%) | **97.9%** | 13 |
| **$\ge 0.90$** | 557 (55.7%) | **99.3%** | 4 |
| **$\ge 0.95$** | **493 (49.3%)** | **99.8%** | **1** |

Of the 493 decisions with reported confidence $\ge 0.95$ (nearly half of all decisions), **492 were correct**.

---

## Positional balance & semantic consistency

![Positional Balance Across Options](charts/option_distribution_balance.svg)

* **Option Selection Uniformity:** Choices were balanced across all five slots:
  * Option 1: **206 (20.6%)**
  * Option 2: **201 (20.1%)**
  * Option 3: **188 (18.8%)**
  * Option 4: **198 (19.8%)**
  * Option 5: **207 (20.7%)**
* **Semantic Invariance:** Across 94 pairs where option order was rotated, Jev chose the same underlying semantic meaning **92.6% of the time** (and **100%** on 15 identical clones), showing that it tracks meaning rather than slot position.

---

## Repository structure

```text
├── README.md                           # This report
├── DIAGNOSTIC_ANALYSIS.md              # Living cumulative diagnostic analysis log
├── run_benchmark.py                    # Multi-channel runner (TypeSafe, OpenRouter, Experiential)
├── test_offline.py                     # Offline test suite (7 tests, 0.22s)
├── docs/
│   └── index.html                      # Interactive Dashboard (GitHub Pages)
├── charts/                             # Standalone publication-grade vector SVG charts
│   ├── reasoning_families_accuracy.svg # 25 families: All vs Core performance
│   ├── confidence_calibration.svg      # Confidence calibration curve
│   ├── failure_modes_f09_f13.svg       # Distractor analysis for F09 & F13
│   └── option_distribution_balance.svg # Positional selection uniformity
├── data/
│   ├── results_1000_eval.csv           # Raw 1,000-decision evaluation results (CSV)
│   └── questions_1000.csv              # Question texts, criteria, and contexts (CSV)
└── .gitignore                          # Protects .env, keys, and private answer keys
```

---

## How to reproduce

```bash
# 1. Run automated offline test suite
python3 test_offline.py

# 2. Dry-run smoke test (no credits spent)
python3 run_benchmark.py --plan smoke

# 3. Live multi-channel execution
python3 run_benchmark.py --plan evaluation --batch-size 400 --execute
```

---

## Data integrity notice
To prevent pre-training benchmark contamination, private answer keys (`*_PRIVATE.csv`) are omitted from public releases. Results, question texts, and evaluation harnesses are open for academic and evaluation use.
