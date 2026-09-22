#!/usr/bin/env python3
"""
Generate standalone, high-resolution SVG graphics representing JEV Benchmark findings (1,000 decisions).
Saves to runs/charts/
"""
import os

OUTPUT_DIR = "/Users/etsabary/Documents/repos/benchmarks/jev/runs/charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. 25-Ability Performance Chart (All vs Core)
def generate_families_svg():
    # (name, all_acc, core_acc, tier_color)
    abilities = [
        ("Record lookup / filtering", 100.0, 100.0, "#10b981"),
        ("Forward conditional reasoning", 100.0, 100.0, "#10b981"),
        ("Transitive comparisons", 100.0, 100.0, "#10b981"),
        ("Directed reachability", 100.0, 100.0, "#10b981"),
        ("Source authority / stale records", 100.0, 100.0, "#10b981"),
        ("Boolean scope / exclusivity", 97.7, 100.0, "#10b981"),
        ("Necessary conditions / contraposition", 97.6, 96.6, "#10b981"),
        ("Quantifiers / set relations", 97.6, 100.0, "#10b981"),
        ("Preference ordering", 97.6, 100.0, "#10b981"),
        ("Fault diagnosis", 97.6, 96.0, "#10b981"),
        ("Rule verification / counterexamples", 97.7, 96.7, "#10b981"),
        ("Temporal interval relations", 97.0, 95.7, "#10b981"),
        ("Planning with preconditions", 94.1, 94.7, "#10b981"),
        ("Exceptions / priority rules", 91.8, 90.9, "#10b981"),
        ("Perspective / belief tracking", 87.8, 88.9, "#38bdf8"),
        ("One-to-one assignments", 84.1, 90.0, "#38bdf8"),
        ("Causal intervention", 80.5, 79.2, "#38bdf8"),
        ("Sufficiency / inconsistency", 79.4, 89.5, "#38bdf8"),
        ("Nested reference binding", 75.6, 64.3, "#38bdf8"),
        ("Scheduling", 67.3, 71.4, "#f59e0b"),
        ("Object tracking through swaps", 61.4, 62.1, "#f97316"),
        ("Truth-teller consistency", 59.5, 57.1, "#f97316"),
        ("Spatial tracking", 52.5, 60.9, "#f97316"),
        ("Exact truth counting (F09)", 33.3, 43.5, "#f43f5e"),
        ("Sequential procedures (F13)", 13.2, 7.7, "#f43f5e"),
    ]

    width = 960
    height = 860
    row_height = 28
    start_y = 100
    bar_x = 310
    max_bar_w = 460

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    svg.append(f'<rect width="{width}" height="{height}" fill="#0f172a" rx="12"/>')
    
    # Title & Header
    svg.append('<text x="40" y="45" fill="#ffffff" font-family="system-ui, -apple-system, sans-serif" font-size="20" font-weight="bold">JEV Decision Benchmark: Capability Across Reasoning Families</text>')
    svg.append('<text x="40" y="70" fill="#94a3b8" font-family="system-ui, -apple-system, sans-serif" font-size="13">Sample: 1,000 decisions (817/1,000 = 81.7% overall) | Solid: All Items | Marker: Core Items</text>')
    
    # Grid lines
    for pct in [0, 25, 50, 75, 100]:
        gx = bar_x + (pct / 100.0) * max_bar_w
        svg.append(f'<line x1="{gx}" y1="85" x2="{gx}" y2="{start_y + len(abilities)*row_height}" stroke="#334155" stroke-dasharray="3,3" stroke-width="1"/>')
        svg.append(f'<text x="{gx}" y="80" fill="#64748b" font-family="system-ui, sans-serif" font-size="11" text-anchor="middle">{pct}%</text>')

    for i, (name, all_acc, core_acc, color) in enumerate(abilities):
        y = start_y + i * row_height
        bar_w = (all_acc / 100.0) * max_bar_w
        core_x = bar_x + (core_acc / 100.0) * max_bar_w
        
        # Family Name
        svg.append(f'<text x="295" y="{y+16}" fill="#e2e8f0" font-family="system-ui, sans-serif" font-size="12" font-weight="500" text-anchor="end">{name}</text>')
        # Background bar
        svg.append(f'<rect x="{bar_x}" y="{y+4}" width="{max_bar_w}" height="16" fill="#1e293b" rx="4"/>')
        # All Value bar
        svg.append(f'<rect x="{bar_x}" y="{y+4}" width="{bar_w}" height="16" fill="{color}" rx="4"/>')
        # Core marker (vertical tick)
        svg.append(f'<line x1="{core_x}" y1="{y+2}" x2="{core_x}" y2="{y+22}" stroke="#ffffff" stroke-width="2.5"/>')
        # All Acc text
        all_str = f"{all_acc:.1f}%" if all_acc < 100 else "100%"
        core_str = f"{core_acc:.1f}%" if core_acc < 100 else "100%"
        svg.append(f'<text x="{bar_x + max_bar_w + 12}" y="{y+16}" fill="#f8fafc" font-family="system-ui, sans-serif" font-size="11" font-weight="bold">{all_str}</text>')
        svg.append(f'<text x="{bar_x + max_bar_w + 62}" y="{y+16}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">Core: {core_str}</text>')

    # Legend
    legend_y = height - 25
    svg.append(f'<rect x="80" y="{legend_y-10}" width="12" height="12" fill="#10b981" rx="3"/>')
    svg.append(f'<text x="100" y="{legend_y}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="11">Very Strong (90-100%)</text>')
    svg.append(f'<rect x="260" y="{legend_y-10}" width="12" height="12" fill="#38bdf8" rx="3"/>')
    svg.append(f'<text x="280" y="{legend_y}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="11">Moderate (75-90%)</text>')
    svg.append(f'<rect x="420" y="{legend_y-10}" width="12" height="12" fill="#f97316" rx="3"/>')
    svg.append(f'<text x="440" y="{legend_y}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="11">Weak (50-75%)</text>')
    svg.append(f'<rect x="560" y="{legend_y-10}" width="12" height="12" fill="#f43f5e" rx="3"/>')
    svg.append(f'<text x="580" y="{legend_y}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="11">Extremely Weak (&lt;35%)</text>')
    svg.append(f'<line x1="740" y1="{legend_y-10}" x2="740" y2="{legend_y+2}" stroke="#ffffff" stroke-width="2.5"/>')
    svg.append(f'<text x="750" y="{legend_y}" fill="#ffffff" font-family="system-ui, sans-serif" font-size="11">Core Benchmark Marker</text>')

    svg.append('</svg>')
    
    path = os.path.join(OUTPUT_DIR, "reasoning_families_accuracy.svg")
    with open(path, "w") as f:
        f.write("\n".join(svg))
    print(f"Saved: {path}")

# 2. Confidence Calibration (1,000 decisions)
def generate_calibration_svg():
    width = 780
    height = 470
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    svg.append(f'<rect width="{width}" height="{height}" fill="#0f172a" rx="12"/>')
    
    # Title
    svg.append('<text x="40" y="45" fill="#ffffff" font-family="system-ui, sans-serif" font-size="18" font-weight="bold">Confidence Calibration & Operational Selectivity (1,000 Decisions)</text>')
    svg.append('<text x="40" y="68" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="12">Empirical accuracy at cumulative confidence thresholds | ROC AUC ≈ 0.93</text>')

    # Graph Area
    gx, gy, gw, gh = 70, 110, 640, 240
    
    # Grid & Y-Axis
    for i, pct in enumerate([80, 85, 90, 95, 100]):
        y = gy + gh - (i / 4.0) * gh
        svg.append(f'<line x1="{gx}" y1="{y}" x2="{gx+gw}" y2="{y}" stroke="#334155" stroke-dasharray="3,3" stroke-width="1"/>')
        svg.append(f'<text x="{gx-12}" y="{y+4}" fill="#64748b" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">{pct}%</text>')

    svg.append(f'<line x1="{gx}" y1="{gy+gh}" x2="{gx+gw}" y2="{gy+gh}" stroke="#475569" stroke-width="1.5"/>')
    svg.append(f'<line x1="{gx}" y1="{gy}" x2="{gx}" y2="{gy+gh}" stroke="#475569" stroke-width="1.5"/>')

    # Points:
    # (cutoff_label, acc, decisions, pct_vol, x_rel)
    data = [
        ("≥ 0.50", 93.4, 786, "78.6%", 0.0),
        ("≥ 0.60", 95.5, 734, "73.4%", 0.2),
        ("≥ 0.70", 96.9, 680, "68.0%", 0.4),
        ("≥ 0.80", 97.9, 632, "63.2%", 0.6),
        ("≥ 0.90", 99.3, 557, "55.7%", 0.8),
        ("≥ 0.95", 99.8, 493, "49.3%", 1.0),
    ]

    pts = []
    for label, acc, decs, vol, xr in data:
        px = gx + xr * gw
        py = gy + gh - ((acc - 80.0) / 20.0) * gh
        pts.append((px, py, label, acc, decs, vol))

    # Area fill
    poly_pts = [f"{gx},{gy+gh}"] + [f"{px},{py}" for px, py, _, _, _, _ in pts] + [f"{gx+gw},{gy+gh}"]
    svg.append(f'<defs><linearGradient id="calGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#38bdf8" stop-opacity="0.3"/><stop offset="100%" stop-color="#38bdf8" stop-opacity="0.0"/></linearGradient></defs>')
    svg.append(f'<polygon points="{" ".join(poly_pts)}" fill="url(#calGrad)"/>')
    
    # Line
    line_pts = " ".join([f"{px},{py}" for px, py, _, _, _, _ in pts])
    svg.append(f'<polyline points="{line_pts}" fill="none" stroke="#38bdf8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')

    # Points & Annotations
    for px, py, label, acc, decs, vol in pts:
        color = "#10b981" if acc >= 99.5 else "#38bdf8"
        r = 7 if acc >= 99.5 else 5
        svg.append(f'<circle cx="{px}" cy="{py}" r="{r}" fill="{color}" stroke="#0f172a" stroke-width="2"/>')
        
        # Accuracy text above point
        svg.append(f'<text x="{px}" y="{py-12}" fill="#f8fafc" font-family="system-ui, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">{acc:.1f}%</text>')
        
        # X-axis label
        svg.append(f'<text x="{px}" y="{gy+gh+22}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="11" font-weight="500" text-anchor="middle">{label}</text>')
        svg.append(f'<text x="{px}" y="{gy+gh+37}" fill="#64748b" font-family="system-ui, sans-serif" font-size="10" text-anchor="middle">({decs} items / {vol})</text>')

    # Banner at bottom
    svg.append(f'<rect x="{gx}" y="{height-42}" width="{gw}" height="28" fill="#1e293b" rx="6"/>')
    svg.append(f'<text x="{width/2}" y="{height-24}" fill="#38bdf8" font-family="system-ui, sans-serif" font-size="11" font-weight="bold" text-anchor="middle">Autonomous Safe Zone: 493 / 1,000 decisions (49.3%) have confidence ≥ 0.95 with 99.8% accuracy (492/493 correct).</text>')

    svg.append('</svg>')
    
    path = os.path.join(OUTPUT_DIR, "confidence_calibration.svg")
    with open(path, "w") as f:
        f.write("\n".join(svg))
    print(f"Saved: {path}")

# 3. Failure Anatomy Chart (1,000 decisions)
def generate_failure_anatomy_svg():
    width = 880
    height = 430
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    svg.append(f'<rect width="{width}" height="{height}" fill="#0f172a" rx="12"/>')
    
    # Title
    svg.append('<text x="40" y="45" fill="#ffffff" font-family="system-ui, sans-serif" font-size="18" font-weight="bold">Anatomy of Signature Failure Modes (1,000 Decisions)</text>')
    svg.append('<text x="40" y="68" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="12">Empirical distractor choices vs. random chance baselines</text>')

    # Column 1: F13 Sequential Procedures
    c1_x, c1_y, cw, ch = 50, 95, 370, 305
    svg.append(f'<rect x="{c1_x}" y="{c1_y}" width="{cw}" height="{ch}" fill="#1e293b" rx="8" stroke="#334155"/>')
    svg.append(f'<text x="{c1_x+16}" y="{c1_y+28}" fill="#f43f5e" font-family="system-ui, sans-serif" font-size="14" font-weight="bold">F13: Sequential Procedures (13.2% All / 7.7% Core)</text>')
    svg.append(f'<text x="{c1_x+16}" y="{c1_y+46}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="11">Stale Intermediate-State Trap (33 errors analyzed)</text>')

    # Sub-bars F13
    svg.append(f'<text x="{c1_x+16}" y="{c1_y+82}" fill="#e2e8f0" font-family="system-ui, sans-serif" font-size="11" font-weight="500">Chose Earlier Valid Sequence State</text>')
    svg.append(f'<rect x="{c1_x+16}" y="{c1_y+92}" width="335" height="14" fill="#0f172a" rx="3"/>')
    svg.append(f'<rect x="{c1_x+16}" y="{c1_y+92}" width="{335 * 0.818}" height="14" fill="#f43f5e" rx="3"/>')
    svg.append(f'<text x="{c1_x+16+335*0.818-6}" y="{c1_y+103}" fill="#ffffff" font-family="system-ui, sans-serif" font-size="10" font-weight="bold" text-anchor="end">81.8% (27/33)</text>')
    svg.append(f'<text x="{c1_x+16}" y="{c1_y+119}" fill="#64748b" font-family="system-ui, sans-serif" font-size="10">Random baseline expectation: ~57.5% (19/33)</text>')

    # Contrast with planning
    svg.append(f'<text x="{c1_x+16}" y="{c1_y+145}" fill="#e2e8f0" font-family="system-ui, sans-serif" font-size="11" font-weight="500">Contrast: Planning with Preconditions</text>')
    svg.append(f'<rect x="{c1_x+16}" y="{c1_y+155}" width="335" height="14" fill="#0f172a" rx="3"/>')
    svg.append(f'<rect x="{c1_x+16}" y="{c1_y+155}" width="{335 * 0.941}" height="14" fill="#10b981" rx="3"/>')
    svg.append(f'<text x="{c1_x+16+335*0.941-6}" y="{c1_y+166}" fill="#ffffff" font-family="system-ui, sans-serif" font-size="10" font-weight="bold" text-anchor="end">94.1% Accuracy</text>')

    # Diagnosis box
    svg.append(f'<rect x="{c1_x+16}" y="{c1_y+190}" width="335" height="95" fill="#0f172a" rx="6" stroke="#475569"/>')
    svg.append(f'<text x="{c1_x+26}" y="{c1_y+210}" fill="#38bdf8" font-family="system-ui, sans-serif" font-size="11" font-weight="bold">Diagnosis: Temporal State Mutation Failure</text>')
    svg.append(f'<text x="{c1_x+26}" y="{c1_y+227}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">JEV easily handles static multi-step relationships,</text>')
    svg.append(f'<text x="{c1_x+26}" y="{c1_y+242}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">but repeatedly mutating and updating state across</text>')
    svg.append(f'<text x="{c1_x+26}" y="{c1_y+257}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">time collapses to earlier visited intermediate states.</text>')
    svg.append(f'<text x="{c1_x+26}" y="{c1_y+274}" fill="#f43f5e" font-family="system-ui, sans-serif" font-size="10" font-weight="bold">Core accuracy: only 2 / 26 correct (7.7%).</text>')

    # Column 2: F09 Exact Truth Counting
    c2_x = 460
    svg.append(f'<rect x="{c2_x}" y="{c1_y}" width="{cw}" height="{ch}" fill="#1e293b" rx="8" stroke="#334155"/>')
    svg.append(f'<text x="{c2_x+16}" y="{c1_y+28}" fill="#f43f5e" font-family="system-ui, sans-serif" font-size="14" font-weight="bold">F09: Exact Truth Counting (33.3% All / 43.5% Core)</text>')
    svg.append(f'<text x="{c2_x+16}" y="{c1_y+46}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="11">Compatibility Maximization Bias (25 errors analyzed)</text>')

    # Sub-bars F09
    svg.append(f'<text x="{c2_x+16}" y="{c1_y+82}" fill="#e2e8f0" font-family="system-ui, sans-serif" font-size="11" font-weight="500">Chose Candidate with MORE Truths Than Required</text>')
    svg.append(f'<rect x="{c2_x+16}" y="{c1_y+92}" width="335" height="14" fill="#0f172a" rx="3"/>')
    svg.append(f'<rect x="{c2_x+16}" y="{c1_y+92}" width="{335 * 0.84}" height="14" fill="#f43f5e" rx="3"/>')
    svg.append(f'<text x="{c2_x+16+335*0.84-6}" y="{c1_y+103}" fill="#ffffff" font-family="system-ui, sans-serif" font-size="10" font-weight="bold" text-anchor="end">84.0% (21/25)</text>')
    svg.append(f'<text x="{c2_x+16}" y="{c1_y+119}" fill="#64748b" font-family="system-ui, sans-serif" font-size="10">Random baseline expectation: ~60.0% (15/25)</text>')

    svg.append(f'<text x="{c2_x+16}" y="{c1_y+145}" fill="#e2e8f0" font-family="system-ui, sans-serif" font-size="11" font-weight="500">Chose Candidate with MAXIMUM Truths Available</text>')
    svg.append(f'<rect x="{c2_x+16}" y="{c1_y+155}" width="335" height="14" fill="#0f172a" rx="3"/>')
    svg.append(f'<rect x="{c2_x+16}" y="{c1_y+155}" width="{335 * 0.64}" height="14" fill="#f59e0b" rx="3"/>')
    svg.append(f'<text x="{c2_x+16+335*0.64-6}" y="{c1_y+166}" fill="#ffffff" font-family="system-ui, sans-serif" font-size="10" font-weight="bold" text-anchor="end">64.0% (16/25)</text>')
    svg.append(f'<text x="{c2_x+16}" y="{c1_y+181}" fill="#64748b" font-family="system-ui, sans-serif" font-size="10">Random baseline expectation: ~28.0% (7/25)</text>')

    # Diagnosis box
    svg.append(f'<rect x="{c2_x+16}" y="{c1_y+190}" width="335" height="95" fill="#0f172a" rx="6" stroke="#475569"/>')
    svg.append(f'<text x="{c2_x+26}" y="{c1_y+210}" fill="#38bdf8" font-family="system-ui, sans-serif" font-size="11" font-weight="bold">Key Breakthrough: Cardinality vs "Exactly"</text>')
    svg.append(f'<text x="{c2_x+26}" y="{c1_y+227}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">Boolean scope (97.7%) handles "exactly one" easily.</text>')
    svg.append(f'<text x="{c2_x+26}" y="{c1_y+242}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">Failure is in cardinality accumulation across items.</text>')
    svg.append(f'<text x="{c2_x+26}" y="{c1_y+257}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">On candidate probes with zero search, JEV scored</text>')
    svg.append(f'<text x="{c2_x+26}" y="{c1_y+274}" fill="#f43f5e" font-family="system-ui, sans-serif" font-size="10" font-weight="bold">0 / 5 (0.0%). The counting operation itself fails.</text>')

    svg.append('</svg>')
    
    path = os.path.join(OUTPUT_DIR, "failure_modes_f09_f13.svg")
    with open(path, "w") as f:
        f.write("\n".join(svg))
    print(f"Saved: {path}")

# 4. Option Distribution & Balance Chart (1,000 decisions)
def generate_option_balance_svg():
    width = 750
    height = 360
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    svg.append(f'<rect width="{width}" height="{height}" fill="#0f172a" rx="12"/>')
    
    # Title
    svg.append('<text x="40" y="45" fill="#ffffff" font-family="system-ui, sans-serif" font-size="18" font-weight="bold">Positional Balance & Semantic Consistency (1,000 Decisions)</text>')
    svg.append('<text x="40" y="68" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="12">Evaluation across 1,000 decisions demonstrates zero positional selection bias</text>')

    # 5 Option Columns
    options = [
        ("Option 1", 206, 20.6),
        ("Option 2", 201, 20.1),
        ("Option 3", 188, 18.8),
        ("Option 4", 198, 19.8),
        ("Option 5", 207, 20.7),
    ]

    ox, oy, total_w, max_h = 70, 260, 380, 140
    col_w = 56
    gap = 24

    # Baseline 20% line
    b_y = oy - (20.0 / 30.0) * max_h
    svg.append(f'<line x1="{ox}" y1="{b_y}" x2="{ox+total_w}" y2="{b_y}" stroke="#38bdf8" stroke-dasharray="3,3" stroke-width="1.5"/>')
    svg.append(f'<text x="{ox+total_w+8}" y="{b_y+4}" fill="#38bdf8" font-family="system-ui, sans-serif" font-size="10" font-weight="bold">Expected 20.0% (200)</text>')

    for i, (name, count, pct) in enumerate(options):
        bx = ox + i * (col_w + gap)
        bh = (pct / 30.0) * max_h
        by = oy - bh
        
        svg.append(f'<rect x="{bx}" y="{by}" width="{col_w}" height="{bh}" fill="#38bdf8" rx="4"/>')
        svg.append(f'<text x="{bx+col_w/2}" y="{by-8}" fill="#ffffff" font-family="system-ui, sans-serif" font-size="11" font-weight="bold" text-anchor="middle">{count}</text>')
        svg.append(f'<text x="{bx+col_w/2}" y="{by-20}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10" text-anchor="middle">{pct}%</text>')
        svg.append(f'<text x="{bx+col_w/2}" y="{oy+18}" fill="#e2e8f0" font-family="system-ui, sans-serif" font-size="11" font-weight="500" text-anchor="middle">{name}</text>')

    # Right Side: Semantic Consistency Cards
    rc_x, rc_y, rc_w = 490, 105, 215
    svg.append(f'<rect x="{rc_x}" y="{rc_y}" width="{rc_w}" height="100" fill="#1e293b" rx="8" stroke="#334155"/>')
    svg.append(f'<text x="{rc_x+14}" y="{rc_y+24}" fill="#10b981" font-family="system-ui, sans-serif" font-size="18" font-weight="bold">92.6%+</text>')
    svg.append(f'<text x="{rc_x+14}" y="{rc_y+44}" fill="#f8fafc" font-family="system-ui, sans-serif" font-size="11" font-weight="bold">Option-Rotated Pairs</text>')
    svg.append(f'<text x="{rc_x+14}" y="{rc_y+62}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">Chooses same semantic concept</text>')
    svg.append(f'<text x="{rc_x+14}" y="{rc_y+76}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">regardless of slot index</text>')

    svg.append(f'<rect x="{rc_x}" y="{rc_y+115}" width="{rc_w}" height="100" fill="#1e293b" rx="8" stroke="#334155"/>')
    svg.append(f'<text x="{rc_x+14}" y="{rc_y+139}" fill="#10b981" font-family="system-ui, sans-serif" font-size="18" font-weight="bold">Stable Semantics</text>')
    svg.append(f'<text x="{rc_x+14}" y="{rc_y+159}" fill="#f8fafc" font-family="system-ui, sans-serif" font-size="11" font-weight="bold">E.g. J001325 Robustness</text>')
    svg.append(f'<text x="{rc_x+14}" y="{rc_y+177}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">Chooses same semantic answer</text>')
    svg.append(f'<text x="{rc_x+14}" y="{rc_y+191}" fill="#94a3b8" font-family="system-ui, sans-serif" font-size="10">across 4 distinct variations</text>')

    svg.append('</svg>')
    
    path = os.path.join(OUTPUT_DIR, "option_distribution_balance.svg")
    with open(path, "w") as f:
        f.write("\n".join(svg))
    print(f"Saved: {path}")

if __name__ == "__main__":
    generate_families_svg()
    generate_calibration_svg()
    generate_failure_anatomy_svg()
    generate_option_balance_svg()
    print("All 1,000-decision SVG graphics successfully updated in:", OUTPUT_DIR)
