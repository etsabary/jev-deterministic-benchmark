# Analysis and interpretation guide
## JEV-DD-1.0

## 1. Interpret a pattern, not a single answer

The earlier JEV results suggested a possible distinction between short deductions and integrating several constraints. That remains one possible explanation. A wrong chest or scheduling answer could also arise from language interpretation, answer-position preference, an incorrect individual truth evaluation, overlooking a clue, or a request-format problem.

This bank combines capability tests with controlled variants, following the broad behavioral-testing approach of CheckList [S3]. Its objective is to make competing explanations more distinguishable through observable decisions. It does not expose the model's internal thoughts.

## 2. The capability profile

| Group | Families | Main distinction |
|---|---|---|
| Reading and binding | F01 record filters; F16 nested references | Finding the right item and connecting names, properties, and roles. |
| Logical rules | F02 forward implication; F03 necessary conditions; F04 Boolean scope; F05 quantifiers | Valid entailment versus reversed implications, scope mistakes, and unsupported existence assumptions. |
| Relations and constraints | F06 comparisons; F07 scheduling; F08 assignments; F09 truth counts; F10 truth-tellers | Local relations versus consistency across a complete candidate world. |
| Evidence sufficiency | F11 unique, underdetermined, and inconsistent cases | A determined outcome versus multiple possible outcomes versus no satisfying world. |
| State, time, and space | F12 swaps; F13 procedures; F14 intervals; F15 spatial commands | Updating a state instead of answering from an earlier or last-mentioned fact. |
| Perspective and intervention | F17 observation-based beliefs; F18 gate overrides | Actual state versus a stipulated observer state; normal operation versus intervention. |
| Explicit decisions and plans | F19 priority exceptions; F20 shortest plans; F21 directed routes; F22 ordered preferences | Any plausible action versus the one allowed or preferred by all relevant rules. |
| Verification and evidence control | F23 counterexamples; F24 authorized current records; F25 fault diagnosis | Checking a rule, respecting source authority, and integrating diagnostic evidence. |

All tasks are finite and self-contained. F17 uses explicit simplified belief-update rules; it is not a general human social-cognition test. F18 uses deterministic circuits; it is not a test of causal discovery from real-world observations. F24 tests a fictional source-authority rule, including an untrusted quoted instruction; it does not constitute a comprehensive security evaluation.

### Levels

Each family has four intended load levels. The actual parameter is recorded in `families.csv` and `parameters_json` in private metadata. Examples include implication-chain lengths of one, two, four, and six; two, four, six, and eight state updates; and verified shortest plans of one to four actions. Scheduling and assignment instances use two to five clues, each necessary for forcing the queried answer. Preference-ordering instances require the final stated priority to break the remaining tie.

The levels are engineered labels. More operations can sometimes cancel or simplify. Longer text and structural difficulty can covary. A level-four item in one family is not necessarily harder than a level-two item in another. Do not fit one global “reasoning capacity” score to these labels.

## 3. What the matched tests measure

There are 100 evaluation anchors, one per family and level. Each has ten meaning-preserving variants and one changed-evidence contrast.

| Variant | What changes | Intended observation |
|---|---|---|
| Four cyclic option rotations | Only the locations of the five options. | Whether a choice follows the same semantic answer when its number changes. |
| Entity renaming | Names are consistently replaced. | Dependence on particular names or name-role associations. |
| Fact-order shuffle | Printed fact order changes; explicit steps, times, and priorities remain attached. | Sensitivity to presentation order rather than the stated order of events. |
| Short irrelevant passage | Unrelated background is inserted. | Distraction sensitivity at modest added length. |
| Long irrelevant passage | Roughly 400 words of unrelated background are inserted. | The additional effect of substantially more irrelevant reading. |
| Expanded option wording | Every option receives the same neutral answer prefix. | Sensitivity to a small increase in option length and framing. |
| Question rewording | The query is expressed in a second form. | Stability under a limited paraphrase. |
| Controlled contrast | One clue, field, command, observation, query direction, or intervention value changes. | Appropriate sensitivity: the correct semantic outcome changes. |

The original plus four rotations covers every correct-answer position, not all 120 possible option permutations. Option-order sensitivity is a documented concern for multiple-choice language-model evaluation [S4]; these tests determine whether it occurs for this particular JEV run.

For invariant pairs, compare semantic outcomes using the private canonical mappings. Comparing the raw option number is wrong when options rotate. Stable-but-wrong decisions are consistent but inaccurate. Correctness and consistency are reported separately.

For contrasts, changing the answer is necessary but insufficient. The strongest success criterion is getting both members correct. `contrast_accuracy_given_base_correct` asks whether the model can adapt on cases it first handled successfully.

The irrelevant passages are explicitly labeled unrelated. This is a controlled distraction test, not a strong test of finding subtly relevant evidence among deceptive near-matches. The expanded-answer condition is a uniform wrapper, not a comprehensive test of very long or semantically elaborate options. The longest prompts remain under 700 words; this is not a context-window-limit benchmark.

## 4. Individual checks versus integrated choices

Eighty supplementary probes belong to 16 anchor puzzles: one parent at each level in F07, F08, F09, and F10. Each parent has five candidate-evaluation questions.

For scheduling and assignment tasks, a probe supplies a complete proposed arrangement and asks how many clues it violates. For chests, it fixes a prize location and asks how many inscriptions become true. For truth-tellers, it fixes a complete assignment of speaker types and asks how many statements disagree with those types.

These probes use the same underlying rules as their parent, while reducing the need to search for the candidate world. They remain separate requests, without feeding probe answers back into the parent request.

| Observed pattern | A supported behavioral interpretation | What it does not establish |
|---|---|---|
| Parent wrong, all five checks correct | The local checks can succeed when the candidate is supplied; the difficulty lies elsewhere in solving or selecting the parent outcome. | A specific hidden search algorithm or a fixed memory limit. |
| Parent wrong, several checks wrong | Difficulty is already visible during local condition evaluation. | That integration would otherwise succeed. |
| Parent right, checks wrong | The two formats yield different performance; investigate shortcuts, guessing, and probe interpretation. | That the parent was necessarily memorized or guessed. |
| Parent and checks correct | Both integrated choice and these local checks succeed. | A guarantee across new families or larger instances. |

Only 16 parent groups are included, so treat this as an initial diagnostic panel. At low clue counts, five count options require some distractors beyond the possible maximum; do not compare probe raw accuracy directly with the primary five-outcome puzzles as an equally calibrated task.

## 5. Reports produced by the analyzer

### Accuracy and coverage

`summary.json`, `accuracy_by_family.csv`, `accuracy_by_level.csv`, and `accuracy_by_family_level.csv` use core first responses only. Default evaluation includes 1,600 core questions: 64 per family and 16 per family-level cell.

Report both accuracy among valid choices and accuracy among all attempted requests. The second counts API or parsing failures as unsuccessful attempts without mislabeling them as logical errors. Coverage shows how much of the intended bank has valid responses. An unattempted item is not an incorrect observed decision.

The full core bank has 80 cases per family and 20 per family-level cell. These are repeated instances of task templates, not 2,000 unrelated real-world decision domains. Five equally likely options give a 20 percent uniform-guessing baseline. Exact balance across the core bank also prevents a constant option-number strategy from exceeding that baseline overall.

### Probability quality

`probability_reliability.csv` bins selected-option probability into ten fixed intervals and compares it with empirical accuracy. `probability_ece_10bins` summarizes the weighted absolute gaps. Small bins are noisy; examine their counts. Calibration is an empirical property of predictions on a population of questions [S5], not something established by the size of one confidence score.

The multiclass Brier score uses the sum of squared deviations of all five probabilities from the one-hot correct answer. Lower is better; the range is zero to two, with 0.8 for a uniform five-option distribution. The log-loss report uses the natural logarithm and clips the correct-answer probability at 1e-15 for finite computation. A separate count reports exact zero probabilities for the gold answer; mathematically these would give infinite log loss.

`reported_confidence_vs_accuracy.csv` treats the provider confidence score separately. It does not label its numerical gap from accuracy as a calibration error because the provider defines it as a distribution-concentration statistic [S2]. `risk_coverage.csv` shows how many decisions remain, and how many are wrong, at different thresholds for both measures. Use development to select an operational threshold, then report its held-out performance; choosing the best threshold after inspecting evaluation is exploratory tuning.

### Robustness, contrasts, and repeats

`paired_robustness.csv` reports paired accuracy changes and semantic consistency. `paired_details.csv` also compares the full distributions after aligning option meanings. Its total-variation distance is zero for identical aligned distributions and can reach one for disjoint distributions.

`rotation_panels.csv` reports all-five-correct and same-meaning-across-five outcomes. `contrast_pairs.csv` reports changed-evidence responses. `component_check_profile.csv` compares parent and candidate-check performance. `repeatability.csv` compares identical inputs with different repeat indices. Repeated calls are never added to the primary core sample size.

`errors_for_review.csv` provides the selected wrong outcome and a verified description of how that candidate fails. These are properties of the candidate answer, not inferred accounts of JEV's internal reasoning. Use them to form targeted follow-up hypotheses.

## 6. Statistical restraint

The analyzer provides descriptive Wilson intervals for proportions. Their independent-case assumption is imperfect because cases share templates. For matched robustness accuracy changes, it additionally resamples whole task-family clusters, retaining matched pairs, to show a sensitivity interval. There are only 25 such clusters and only four anchors per family. Treat these intervals as descriptive uncertainty summaries, not as proof that this small suite represents every deployment context.

Do not count a parent, its ten paraphrases/rotations, its contrast, and its repeated presentations as many independent confirmations of the same ability. Avoid emphasizing isolated best or worst level cells with only 16 evaluation cases. Examine error counts, effect sizes, pair completeness, and convergence across related families. Many comparisons are exploratory; the package does not perform a family of significance tests or adjust p-values.

## 7. Validation and boundaries

All 3,180 supplied keys were recomputed with explicit solvers or deterministic simulations. Validation checks five distinct options, prompt hashes, balanced core positions, correct canonical mappings, meaning-preserving specifications, and all 100 changed-outcome contrasts. Selected families have additional cross-checks using a different computation, including Boolean propagation versus exhaustive assignments and forward versus reverse planning search. Core intervention cases are checked to change the normal output and to include the no-intervention outcome as a distractor.

The analyzer has been tested with synthetic perfect, constant-choice, invalid-response, and repeat-response data. Those are software tests, not JEV performance measurements. The supplied result fields remain blank.

The English renderers and primary solvers share formal specifications. That prevents many numerical and logical key errors but does not independently validate every linguistic interpretation. Sample items have been inspected during construction; a separate blinded human review has not been performed. Freeze this version for a run. If a wording defect is discovered, retain the old version, mark the affected item, and produce a versioned correction rather than silently changing its key after seeing model responses.

No finite bank covers all deterministic decisions. This version excludes open-ended response generation, external tool use, probabilistic decisions, visual reasoning, specialized factual knowledge, and real-world safety validation. It does not measure a human school grade, IQ, or fixed working-memory capacity. New parameterized instances reduce reliance on exact familiar riddle wording but do not prove that the underlying task patterns were absent from training. Development and evaluation share templates, so this split measures held-out instances, not unseen-template generalization.

## 8. Methodological references

[S2] TypeSafe AI. *Confidence*. `https://docs.typesafe.ai/confidence`

[S3] Ribeiro, M. T., Wu, T., Guestrin, C., and Singh, S. (2020). *Beyond Accuracy: Behavioral Testing of NLP Models with CheckList*. Proceedings of ACL, 4902–4912. `https://aclanthology.org/2020.acl-main.442/`

[S4] Pezeshkpour, P., and Hruschka, E. (2023). *Large Language Models Sensitivity to The Order of Options in Multiple-Choice Questions*. `https://arxiv.org/abs/2308.11483`

[S5] Guo, C., Pleiss, G., Sun, Y., and Weinberger, K. Q. (2017). *On Calibration of Modern Neural Networks*. `https://arxiv.org/abs/1706.04599`

The references motivate the API mapping and evaluation design. The generated questions are not copied from these papers.
