import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

try:
    import pygmo as pg
except Exception:
    pg = None

try:
    from general_helpers import CURRENCY, extract_pareto_arrays, get_changed_pipes, money
except Exception:
    CURRENCY = "€"


def _cost(value):
    return f"{CURRENCY}{value:,.0f}"


def _style_table(table, n_cols, total_row=None):
    """Keep the tutorial tables looking similar."""
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)

    for col in range(n_cols):
        table[0, col].set_facecolor("#f0f0f0")
        table[0, col].set_text_props(fontweight="bold")

        if total_row is not None:
            table[total_row, col].set_facecolor("#f0f0f0")
            table[total_row, col].set_text_props(fontweight="bold")

    return table


def _tidy_report(report):
    """Make old/new report dictionaries use the same names."""
    if "total_cost" not in report and "cost" in report:
        report["total_cost"] = report["cost"]

    if "stage_deficits" not in report and "stage_deficit_matrix" in report:
        report["stage_deficits"] = np.max(report["stage_deficit_matrix"], axis=0)

    return report


def compare_static_vs_staged_results(
    model_static,
    model_staged,
    pop_static,
    pop_staged,
    static_problem,
    staged_problem,
    static_label="Static (2090 demand)",
    staged_label="Staged (2030–90)",
):
    """Compare the best static and staged solutions."""

    best_static_x = static_problem.repair(pop_static.champion_x)
    static_report = model_static.calculateObjectives(best_static_x, return_report=True)
    static_report = _tidy_report(static_report)

    best_staged_x = staged_problem.repair(pop_staged.champion_x)
    staged_report = model_staged.calculateObjectives(best_staged_x, return_report=True)
    staged_report = _tidy_report(staged_report)

    static_cost = static_report["total_cost"]
    nominal_total = sum(staged_report["stage_nominal_costs"])
    pv_total = sum(staged_report["stage_discounted_costs"])
    deficit_total = sum(staged_report["stage_deficits"])

    saving = static_cost - pv_total
    saving_pct = 100 * saving / static_cost

    x_matrix = best_staged_x.reshape(model_staged.n_stages, model_staged.n_pipes)
    stage_notes = get_changed_pipes(x_matrix)

    payments = []
    for i, year in enumerate(model_staged.CONSTRUCTION_YEARS):
        cost = staged_report["stage_nominal_costs"][i]
        if cost > 0:
            when = "today" if i == 0 else f"in {year}"
            payments.append(f"{_cost(cost)} {when}")

    fig, axes = plt.subplots(2, 1, figsize=(10, 6))
    fig.patch.set_facecolor("white")

    axes[0].axis("off")
    axes[0].set_title("Static vs Staged Comparison", fontweight="bold", fontsize=12, pad=10)

    summary_rows = [
        [
            static_label,
            _cost(static_cost),
            _cost(static_cost),
            _cost(static_cost),
            f"{static_report['total_deficit']:.2f}",
        ],
        [
            staged_label,
            _cost(staged_report["stage_nominal_costs"][0]),
            _cost(pv_total),
            _cost(nominal_total),
            f"{deficit_total:.2f}",
        ],
        ["Saving", "", f"{_cost(saving)}  ({saving_pct:.1f}%)", "", ""],
    ]

    t1 = axes[0].table(
        cellText=summary_rows,
        colLabels=["", "Initial cost", "PV cost", "Nominal cost", "Deficit"],
        cellLoc="center",
        loc="upper center",
        colWidths=[0.25, 0.18, 0.22, 0.18, 0.12],
    )
    _style_table(t1, n_cols=5, total_row=3)

    axes[1].axis("off")
    axes[1].set_title(
        "Stage-by-stage breakdown (Staged design)",
        fontweight="bold",
        fontsize=12,
        pad=5,
    )

    stage_rows = []
    for i, year in enumerate(model_staged.CONSTRUCTION_YEARS):
        stage_rows.append([
            str(year),
            stage_notes[i],
            _cost(staged_report["stage_nominal_costs"][i]),
            _cost(staged_report["stage_discounted_costs"][i]),
            f"{staged_report['stage_deficits'][i]:.2f}",
        ])

    stage_rows.append(["Total", "", _cost(nominal_total), _cost(pv_total), f"{deficit_total:.2f}"])

    t2 = axes[1].table(
        cellText=stage_rows,
        colLabels=["Year", "Pipes changed", "Nominal cost", "PV cost", "Deficit"],
        cellLoc="center",
        loc="upper center",
        colWidths=[0.10, 0.28, 0.20, 0.20, 0.12],
    )
    _style_table(t2, n_cols=5, total_row=len(stage_rows))

    plt.tight_layout()
    plt.show()

    print("\n  What does the utility actually pay?")
    print(f"  Static : {_cost(static_cost)} today")
    print(f"  Staged : {'  →  '.join(payments)}")
    print(f"  PV saving : {_cost(saving)}  ({saving_pct:.1f}% cheaper in today's money)")

    return {
        "best_static_x": best_static_x,
        "best_staged_x": best_staged_x,
        "static_report": static_report,
        "staged_report": staged_report,
        "static_cost": static_cost,
        "staged_nominal_total": nominal_total,
        "staged_pv_total": pv_total,
        "saving": saving,
        "saving_pct": saving_pct,
    }


def get_cheapest_feasible_idx(pareto_records, tolerance=1e-8):
    """Index of the cheapest solution with zero total deficit."""
    _, _, _, _, total_deficit = extract_pareto_arrays(pareto_records)

    feasible = total_deficit <= tolerance
    if feasible.any():
        return int(np.argmax(feasible))

    return None


def display_pareto_summary_table(
    pareto_records,
    n_rows_to_show=15,
    include_cheapest_feasible=True,
):
    """Show a compact table of selected Pareto solutions."""

    costs, surplus_min, surplus_avg, surplus_max, total_deficit = extract_pareto_arrays(
        pareto_records
    )

    idx_to_show = np.linspace(
        0,
        len(pareto_records) - 1,
        min(n_rows_to_show, len(pareto_records)),
    ).astype(int)

    if include_cheapest_feasible:
        cheapest_idx = get_cheapest_feasible_idx(pareto_records)
        if cheapest_idx is not None:
            idx_to_show = np.unique(np.r_[idx_to_show, cheapest_idx])

    cost_col = f"Cost ({CURRENCY})"
    pareto_summary = pd.DataFrame({
        cost_col: costs[idx_to_show],
        "Worst-case minimum surplus": surplus_min[idx_to_show],
        "Average minimum surplus": surplus_avg[idx_to_show],
        "Best-case minimum surplus": surplus_max[idx_to_show],
        "Band width": surplus_max[idx_to_show] - surplus_min[idx_to_show],
        "Total deficit": total_deficit[idx_to_show],
    })

    display(
        pareto_summary.style
        .hide(axis="index")
        .format({
            cost_col: CURRENCY + "{:,.0f}",
            "Worst-case minimum surplus": "{:.3f} m",
            "Average minimum surplus": "{:.3f} m",
            "Best-case minimum surplus": "{:.3f} m",
            "Band width": "{:.3f} m",
            "Total deficit": "{:.2f}",
        })
    )

    return pareto_summary


def build_pareto_records(population, problem_instance, model):
    """Rebuild the Pareto records from a PyGMO population."""
    if pg is None:
        raise ImportError("pygmo is needed to build Pareto records.")

    F = np.array(population.get_f())
    X = np.array(population.get_x())

    ndf, _, _, _ = pg.fast_non_dominated_sorting(F)
    pareto_idx = np.array(ndf[0])

    pareto_records = []

    for original_idx in pareto_idx:
        x_rep = problem_instance.repair(X[original_idx])
        report = model.calculateObjectives(x_rep, return_report=True)

        surplus_per_scenario = np.array(report["surplus_per_scenario"])

        pareto_records.append({
            "original_idx": int(original_idx),
            "x": x_rep,

            "cost": report["cost"],
            "surplus_min": float(np.min(surplus_per_scenario)),
            "surplus_avg": float(np.mean(surplus_per_scenario)),
            "surplus_max": float(np.max(surplus_per_scenario)),

            "total_deficit": report["total_deficit"],
            "total_penalty_deficit": report["total_penalty_deficit"],

            "surplus_per_scenario": surplus_per_scenario,
            "stage_surplus_matrix": report["stage_surplus_matrix"],
            "stage_deficit_matrix": report["stage_deficit_matrix"],
            "stage_min_pressure_matrix": report["stage_min_pressure_matrix"],
        })

    return sorted(pareto_records, key=lambda r: r["cost"])


def summarise_flexible_solution(pop_flexible, flex_problem, model):
    """Show the best flexible solution and the branch costs by scenario."""

    best_x = pop_flexible.champion_x
    best_x_rep = flex_problem.repair(best_x)

    stage1, later = flex_problem._decode(best_x_rep)
    stage1 = stage1.astype(int)

    stage1_cost = float(np.sum(model.UNIT_COST[stage1] * model.pipe_lengths))
    expected_cost = model.calculateExpectedCost(stage1, later)

    scenario_results = []
    total_deficit = 0.0

    for s, sc in enumerate(model.DEMAND_SCENARIOS):
        branch_cost = model.calculateBranchCost(stage1, later[s], s)
        deficit = model.evaluateScenario(stage1, later[s], sc)
        total_deficit += deficit

        scenario_results.append({
            "scenario": f"SC{s + 1}",
            "branch_cost": branch_cost,
            "deficit": deficit,
        })

    fig, axes = plt.subplots(2, 1, figsize=(10, 6))
    fig.patch.set_facecolor("white")

    axes[0].axis("off")
    axes[0].set_title("Flexible Design – Summary", fontweight="bold", fontsize=12, pad=10)

    t1 = axes[0].table(
        cellText=[["Flexible (2030–2090)", _cost(stage1_cost), _cost(expected_cost), f"{total_deficit:.2f}"]],
        colLabels=["", "Initial cost (2030)", "Expected PV cost", "Total deficit"],
        cellLoc="center",
        loc="upper center",
        colWidths=[0.30, 0.24, 0.24, 0.16],
    )
    _style_table(t1, n_cols=4)

    axes[1].axis("off")
    axes[1].set_title(
        "Per-scenario breakdown (Flexible design)",
        fontweight="bold",
        fontsize=12,
        pad=5,
    )

    rows = []
    for result in scenario_results:
        warning = "  ⚠" if result["deficit"] > 0 else ""
        rows.append([
            result["scenario"],
            _cost(result["branch_cost"]),
            f"{result['deficit']:.2f}{warning}",
        ])

    rows.append(["Expected", _cost(expected_cost), f"{total_deficit:.2f}"])

    t2 = axes[1].table(
        cellText=rows,
        colLabels=["Scenario", "Branch Total PV cost", "Deficit"],
        cellLoc="center",
        loc="upper center",
        colWidths=[0.20, 0.40, 0.30],
    )
    _style_table(t2, n_cols=3, total_row=len(rows))

    plt.tight_layout()
    plt.show()

    print("\n  What does the utility actually pay?")
    print(f"  Immediate commitment  : {_cost(stage1_cost)} today")

    return {
        "best_x": best_x,
        "best_x_repaired": best_x_rep,
        "stage1": stage1,
        "later": later,
        "stage1_cost": stage1_cost,
        "expected_cost": expected_cost,
        "scenario_results": scenario_results,
    }

def compare_robust_vs_flexible_strategies(
    model_robust,
    flex_model,
    pareto_records,
    stage1,
    later,
):
    """
    Compare the robust and flexible strategies.

    Robust:
    - one pathway that works for all scenarios

    Flexible:
    - one first-stage decision
    - later decisions can change by scenario
    """

    feasible_indices = [
        i for i, r in enumerate(pareto_records)
        if r["total_deficit"] == 0
    ]

    if len(feasible_indices) == 0:
        print("⚠ No robust solution with zero deficit — using the lowest-deficit one.")
        robust_idx = int(np.argmin([r["total_deficit"] for r in pareto_records]))
    else:
        robust_idx = min(
            feasible_indices,
            key=lambda i: pareto_records[i]["cost"]
        )

    robust_record = pareto_records[robust_idx]
    robust_cost = robust_record["cost"]
    x_robust = robust_record["x"]

    robust_report = model_robust.calculateObjectives(
        x_robust,
        return_report=True
    )

    robust_stage1_cost = robust_report["stage_nominal_costs"][0]

    stage1 = stage1.astype(int)

    flex_stage1_cost = float(np.sum(
        flex_model.UNIT_COST[stage1] * flex_model.pipe_lengths
    ))

    flex_expected_cost = flex_model.calculateExpectedCost(stage1, later)

    saving = robust_cost - flex_expected_cost

    W = 55
    print("─" * W)
    print(f"{'':20} {'Robust':>15}  {'Flexible':>15}")
    print("─" * W)
    print(f"{'Initial commitment':20} €{robust_stage1_cost:>13,.0f}  €{flex_stage1_cost:>13,.0f}")
    print(f"{'Expected total cost':20} €{robust_cost:>13,.0f}  €{flex_expected_cost:>13,.0f}")
    print(f"{'Saving (flexible)':20} {'':>15}  €{saving:>13,.0f}")
    print("─" * W)

    return {
        "robust_idx": robust_idx,
        "robust_record": robust_record,
        "robust_report": robust_report,
        "robust_stage1_cost": robust_stage1_cost,
        "robust_cost": robust_cost,
        "flex_stage1_cost": flex_stage1_cost,
        "flex_expected_cost": flex_expected_cost,
        "saving_flexible": saving,
    }