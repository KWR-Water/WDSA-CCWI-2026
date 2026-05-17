import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

try:
    import pygmo as pg
except Exception:
    pg = None

try:
    from general_helpers import CURRENCY, extract_pareto_arrays, money
except Exception:
    CURRENCY = "$"


def _cost(value):
    return f"{CURRENCY}{value:,.0f}"


def _cost_axis(ax, axis="x"):
    formatter = StrMethodFormatter(CURRENCY + "{x:,.0f}")
    if axis == "x":
        ax.xaxis.set_major_formatter(formatter)
    else:
        ax.yaxis.set_major_formatter(formatter)


def _simple_grid(ax):
    ax.grid(True, alpha=0.25)
    return ax


def _cheapest_feasible_idx(pareto_records, tolerance=1e-8):
    _, _, _, _, total_deficit = extract_pareto_arrays(pareto_records)
    feasible = total_deficit <= tolerance
    if feasible.any():
        return int(np.argmax(feasible))
    return None


def _report_values(report, n_stages, key, fallback_key=None, reducer=None):
    if key in report:
        values = np.asarray(report[key], dtype=float)
    elif fallback_key is not None and fallback_key in report:
        raw = np.asarray(report[fallback_key], dtype=float)
        values = reducer(raw) if reducer is not None else raw
    else:
        values = np.full(n_stages, np.nan)

    if values.ndim == 0:
        values = np.array([float(values)])

    if len(values) < n_stages:
        values = np.r_[values, np.full(n_stages - len(values), np.nan)]

    return values[:n_stages]


def _value_or_dash(value, decimals=2):
    if value is None or np.isnan(value):
        return "—"
    return f"{value:.{decimals}f}"


def _money_or_dash(value):
    if value is None or np.isnan(value):
        return "—"
    return _cost(value)


def plot_staged_solution_pathway(
    model,
    x_repaired,
    report=None,
    title="Staged upgrade pathway",
    fontsize=10,
    x_spacing=1.6,
    stage1_facecolor=None,
    later_facecolor=None,
    ax=None,
    trailing_arrow_to=None,
):
    """Draw one staged design as a left-to-right pathway."""

    stage1_facecolor = stage1_facecolor or "#E3F2FD"
    later_facecolor = later_facecolor or "#F5F5F5"
    dark_blue = "#1f4e79"

    x = np.asarray(x_repaired).astype(int)

    if x.ndim == 2:
        x_matrix = x
        n_stages, n_pipes = x_matrix.shape
    else:
        x = x.ravel()
        n_pipes = int(model.n_pipes)

        if len(x) == n_pipes:
            n_stages = 1
            x_matrix = x.reshape(1, n_pipes)
        else:
            model_n_stages = getattr(model, "n_stages", None)

            if model_n_stages is not None and len(x) == model_n_stages * n_pipes:
                n_stages = int(model_n_stages)
            elif len(x) % n_pipes == 0:
                n_stages = len(x) // n_pipes
            else:
                raise ValueError(
                    "Could not reshape x_repaired into stages and pipes. "
                    f"Received length {len(x)} with n_pipes={n_pipes}."
                )

            x_matrix = x.reshape(n_stages, n_pipes)

    years = getattr(model, "CONSTRUCTION_YEARS", None)
    if years is None or len(years) < n_stages:
        years = [f"Stage {i + 1}" for i in range(n_stages)]

    diameters = getattr(model, "AVAILABLE_DIAMETERS", None)
    report = report or {}

    stage_nominal_costs = _report_values(report, n_stages, "stage_nominal_costs")
    stage_discounted_costs = _report_values(report, n_stages, "stage_discounted_costs")
    stage_deficits = _report_values(
        report,
        n_stages,
        "stage_deficits",
        fallback_key="stage_deficit_matrix",
        reducer=lambda a: np.max(a, axis=0),
    )

    
    if n_stages == 1:
        if np.isnan(stage_nominal_costs[0]):
            stage_nominal_costs[0] = report.get("total_cost", report.get("cost", np.nan))
        if np.isnan(stage_discounted_costs[0]):
            stage_discounted_costs[0] = report.get("total_cost", report.get("cost", np.nan))
        if np.isnan(stage_deficits[0]):
            stage_deficits[0] = report.get("total_deficit", np.nan)

    def diameter_label(diameter_idx):
        if diameters is None:
            return f"D{diameter_idx}"
        try:
            return f"{int(diameters[diameter_idx])} mm"
        except Exception:
            return f"D{diameter_idx}"

    if ax is None:
        _, ax = plt.subplots(figsize=(max(8, n_stages * 3), 4.8))

    ax.set_axis_off()

    y = 0
    previous = np.full(n_pipes, -1, dtype=int)

    for stage in range(n_stages):
        design = x_matrix[stage]
        changed = np.where(design != previous)[0]

        if stage == 0:
            changed = np.arange(n_pipes)

        if len(changed) == 0:
            pipe_lines = ["No pipe changes"]
        else:
            pipe_lines = [
                f"P{p + 1}: {diameter_label(design[p])}"
                for p in changed
            ]

        box_text = (
            f"Stage {stage + 1}\n"
            f"({years[stage]})\n"
            f"{'─' * 16}\n"
            + "\n".join(pipe_lines)
            + f"\n{'─' * 16}\n"
            f"Nominal: {_money_or_dash(stage_nominal_costs[stage])}\n"
            f"PV: {_money_or_dash(stage_discounted_costs[stage])}\n"
            f"Deficit: {_value_or_dash(stage_deficits[stage])}"
        )

        x_pos = stage * x_spacing
        facecolor = stage1_facecolor if stage == 0 else later_facecolor

        ax.text(
            x_pos,
            y,
            box_text,
            ha="center",
            va="center",
            fontsize=fontsize,
            bbox=dict(
                boxstyle="round,pad=0.55",
                facecolor=facecolor,
                edgecolor="#333333",
                linewidth=1.1,
                alpha=0.98,
            ),
            zorder=3,
        )

        if stage > 0:
            ax.annotate(
                "",
                xy=(x_pos - 0.42, y),
                xytext=((stage - 1) * x_spacing + 0.42, y),
                arrowprops=dict(
                    arrowstyle="->",
                    color=dark_blue,
                    linewidth=1.8,
                    alpha=0.75,
                ),
                zorder=2,
            )

        previous = design.copy()

    if trailing_arrow_to is not None:
        last_x = (n_stages - 1) * x_spacing

        ax.annotate(
            "",
            xy=(trailing_arrow_to, y),
            xytext=(last_x + 0.5, y),
            arrowprops=dict(
                arrowstyle="->",
                color=dark_blue,
                linewidth=1.8,
                alpha=0.55,
            ),
            zorder=2,
        )

        ax.text(
            (last_x + trailing_arrow_to) / 2,
            y + 0.55,
            "same design retained",
            ha="center",
            va="bottom",
            fontsize=max(fontsize - 1, 8),
            color="#555555",
        )

    ax.set_title(title, fontsize=max(fontsize + 2, 12), fontweight="bold", pad=18)

    xmax = max(
        (n_stages - 1) * x_spacing + 0.75,
        trailing_arrow_to + 0.4 if trailing_arrow_to is not None else 0,
    )
    ax.set_xlim(-0.75, xmax)
    ax.set_ylim(-1.2, 1.2)

    return ax


def plot_selected_robust_pathway(chosen_idx, pareto_records, model_robust):
    """Plot one selected robust pathway from the Pareto list."""

    record = pareto_records[chosen_idx]
    x_repaired = record["x"]

    report = model_robust.calculateObjectives(x_repaired, return_report=True)

    if "total_cost" not in report and "cost" in report:
        report["total_cost"] = report["cost"]

    if "stage_deficits" not in report and "stage_deficit_matrix" in report:
        report["stage_deficits"] = np.max(report["stage_deficit_matrix"], axis=0)

    fig, ax = plt.subplots(figsize=(12, 6))

    title = (
        f"Chosen Robust Pathway (Solution ID: {chosen_idx})\n"
        f"Cost: {_cost(record['cost'])} | Worst-case Surplus: {record['surplus_min']:.2f} m"
    )

    plot_staged_solution_pathway(
        model=model_robust,
        x_repaired=x_repaired,
        report=report,
        title=title,
        fontsize=10,
        x_spacing=2.2,
        stage1_facecolor="#E3F2FD",
        later_facecolor="#F5F5F5",
        ax=ax,
    )

    plt.tight_layout()
    plt.show()


def plot_static_vs_staged_pathways(
    model_static,
    best_static_x,
    static_report,
    model_staged,
    best_staged_x,
    staged_report,
    figsize=(14, 12),
    x_spacing=1.5,
):
    """Put the static and staged pathway diagrams one above the other."""

    n_stages_staged = model_staged.n_stages
    total_width = (n_stages_staged - 1) * x_spacing

    fig, axes = plt.subplots(2, 1, figsize=figsize)

    plot_staged_solution_pathway(
        model=model_static,
        x_repaired=best_static_x,
        report=static_report,
        title="Static Design — Built entirely in 2030, sized for 2090 demand",
        fontsize=11,
        x_spacing=x_spacing,
        trailing_arrow_to=total_width + 0.5,
        ax=axes[0],
    )
    axes[0].set_xlim(-1.0, total_width + 1.0)

    plot_staged_solution_pathway(
        model=model_staged,
        x_repaired=best_staged_x,
        report=staged_report,
        title="Staged Design — Upgrades spread across 2030–2090",
        fontsize=11,
        x_spacing=x_spacing,
        ax=axes[1],
    )

    plt.suptitle("Static vs Staged Upgrade Pathway", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.show()


def plot_optimisation_progress(algorithms, titles, main_title="Optimisation Progress"):
    """Plot the progress logs from one or more PyGMO algorithms."""
    if pg is None:
        raise ImportError("pygmo is needed to read the optimisation logs.")

    n_plots = len(algorithms)
    fig, axes = plt.subplots(1, n_plots, figsize=(6.5 * n_plots, 5))
    fig.patch.set_facecolor("white")

    if n_plots == 1:
        axes = [axes]

    for ax, algo, title in zip(axes, algorithms, titles):
        algo_name = algo.get_name().lower()

        if "sade" in algo_name:
            logs = algo.extract(pg.sade).get_log()
            generations = [entry[0] for entry in logs]
            fitness = [entry[2] for entry in logs]

            ax.plot(generations, fitness, marker="o", linewidth=2, color="#2ca02c")
            ax.set_ylabel(f"NPV ({CURRENCY})")
            _cost_axis(ax, "y")
            ax.set_title(title, fontweight="bold")

        elif "nsga" in algo_name or "nsga2" in algo_name:
            logs = algo.extract(pg.nsga2).get_log()
            generations = [entry[0] for entry in logs]
            ideal_cost = [entry[3] for entry in logs]
            ideal_surplus = [-entry[4] for entry in logs]

            ax_twin = ax.twinx()

            cost_line = ax.plot(
                generations,
                ideal_cost,
                marker="o",
                linewidth=2,
                color="#1f77b4",
                label="Lowest cost",
            )
            ax.set_ylabel(f"Lowest cost found ({CURRENCY})", color="#1f77b4")
            ax.tick_params(axis="y", labelcolor="#1f77b4")
            _cost_axis(ax, "y")

            surplus_line = ax_twin.plot(
                generations,
                ideal_surplus,
                marker="s",
                linestyle="--",
                linewidth=2,
                color="#ff7f0e",
                label="Highest safety margin",
            )
            ax_twin.set_ylabel("Highest min surplus (m)", color="#ff7f0e")
            ax_twin.tick_params(axis="y", labelcolor="#ff7f0e")

            lines = cost_line + surplus_line
            labels = [line.get_label() for line in lines]
            ax.legend(lines, labels, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
            ax.set_title(title, fontweight="bold")

        ax.set_xlabel("Generation")
        ax.grid(True, linestyle="--", alpha=0.6)

    plt.suptitle(main_title, fontsize=14, fontweight="bold", y=1.05)
    plt.tight_layout()
    plt.show()


def plot_robust_pareto_front(pareto_records, algo=None, title=None):
    """Plot the robust Pareto front with the scenario surplus band."""

    costs, surplus_min, surplus_avg, surplus_max, _ = extract_pareto_arrays(pareto_records)
    cheapest_idx = _cheapest_feasible_idx(pareto_records)

    if algo is not None:
        fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
        ax_pareto = axes[0]
        axes[1].axis("off")
    else:
        fig, ax_pareto = plt.subplots(figsize=(10, 5.5))

    dark_blue = "#1f4e79"
    mid_blue = "#5b9bd5"
    light_blue = "#d9eaf7"

    ax_pareto.fill_between(
        costs,
        surplus_min,
        surplus_max,
        color=light_blue,
        alpha=0.65,
        label="Scenario range",
    )
    ax_pareto.plot(
        costs,
        surplus_min,
        "o-",
        color=dark_blue,
        linewidth=2.2,
        markersize=5,
        label="Worst-case minimum surplus",
    )
    ax_pareto.plot(
        costs,
        surplus_avg,
        ".-",
        color=mid_blue,
        linewidth=1.3,
        markersize=4,
        alpha=0.75,
        label="Average minimum surplus",
    )
    ax_pareto.plot(
        costs,
        surplus_max,
        "o--",
        color=dark_blue,
        linewidth=1.4,
        markersize=4,
        alpha=0.75,
        label="Best-case minimum surplus",
    )

    if cheapest_idx is not None:
        ax_pareto.plot(
            costs[cheapest_idx],
            surplus_min[cheapest_idx],
            "*",
            color=dark_blue,
            markersize=15,
            zorder=5,
            label=f"Cheapest feasible ({_cost(costs[cheapest_idx])})",
        )

    ax_pareto.axhline(
        0,
        color="black",
        linestyle="-",
        linewidth=1.1,
        alpha=0.45,
        label="Feasibility boundary (0 m)",
    )

    ax_pareto.set_xlabel(f"Total discounted cost — NPV ({CURRENCY})", fontsize=11)
    ax_pareto.set_ylabel("Minimum pressure surplus (m)", fontsize=11)
    ax_pareto.set_title(
        title or "Robust Pareto Front: Cost vs Worst-Case Surplus",
        fontsize=12,
        fontweight="bold",
    )
    _simple_grid(ax_pareto)
    ax_pareto.legend(fontsize=9, loc="lower right")
    _cost_axis(ax_pareto, "x")

    plt.tight_layout()
    plt.show()


def plot_flexible_pathway_tree(
    model,
    stage1,
    later,
    scale_labels=None,
    title="Flexible Pathway Map",
    figsize=(18, 20),
):
    """Draw the adaptive solution as a small decision tree."""

    stage1_blue = "#E3F2FD"
    shared_grey = "#EEEEEE"
    branch_grey = "#F5F5F5"
    dark_blue = "#1f4e79"
    border_colour = "#333333"

    stage1 = np.asarray(stage1).astype(int)

    if scale_labels is None:
        scale_labels = [f"SC{i + 1}" for i in range(model.n_scenarios)]

    branches = np.zeros((model.n_scenarios, model.n_stages, model.n_pipes), dtype=int)
    for s in range(model.n_scenarios):
        full = np.concatenate([stage1, later[s]]).reshape(model.n_stages, model.n_pipes)
        branches[s] = full

    stage1_cost = float(np.sum(model.UNIT_COST[stage1] * model.pipe_lengths))

    n_scenarios = len(scale_labels)
    n_stages = model.n_stages

    scenario_costs = np.array([
        model.calculateBranchCost(stage1, branches[s, 1:, :].ravel(), s)
        for s in range(n_scenarios)
    ])

    y_space = 10
    y_scenario = np.arange(n_scenarios - 1, -1, -1) * y_space
    x_spacing = 1.0

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_axis_off()

    nodes = {}
    scenario_paths = {s: [] for s in range(n_scenarios)}

    for stage in range(n_stages):
        stage_designs = branches[:, stage, :]
        unique_designs, inverse_indices = np.unique(
            stage_designs,
            axis=0,
            return_inverse=True,
        )

        for i, design in enumerate(unique_designs):
            scens = np.where(inverse_indices == i)[0]
            node_key = (stage, tuple(design))
            scen_list = ", ".join(f"S{s + 1}" for s in scens)

            if stage == 0:
                body = "\n".join(
                    f"P{p + 1}: {int(model.AVAILABLE_DIAMETERS[design[p]])}mm"
                    for p in range(model.n_pipes)
                )
                footer = f"\n{'-' * 15}\nInit cost: {_cost(stage1_cost)}"
            else:
                prev_key = scenario_paths[scens[0]][stage - 1]
                prev_design = np.array(prev_key[1])
                changed = design != prev_design

                if changed.any():
                    body = "\n".join(
                        f"P{p + 1}: {int(model.AVAILABLE_DIAMETERS[design[p]])}mm"
                        for p in np.where(changed)[0]
                    )
                else:
                    body = "No changes"
                footer = ""

            if stage == n_stages - 1:
                cost_vals = [scenario_costs[s] for s in scens]

                demand_text = (
                    f"{scale_labels[scens[0]]}"
                    if len(scens) == 1
                    else f"{scale_labels[scens[0]]} → {scale_labels[scens[-1]]}"
                )
                cost_text = (
                    _cost(cost_vals[0])
                    if len(scens) == 1
                    else f"{_cost(min(cost_vals))} – {_cost(max(cost_vals))}"
                )
                footer = f"\n{'-' * 15}\n{demand_text}\n{cost_text}"

            y_coord = np.mean([y_scenario[s] for s in scens])
            nodes[node_key] = {
                "pos": (stage * x_spacing, y_coord),
                "text": f"[{scen_list}]\n{'-' * 15}\n{body}{footer}",
                "scens": scens,
                "stage": stage,
            }

            for s in scens:
                scenario_paths[s].append(node_key)

    # Draw branches first so the boxes sit on top.
    for s in range(n_scenarios):
        path = scenario_paths[s]
        for step in range(len(path) - 1):
            start = nodes[path[step]]["pos"]
            end = nodes[path[step + 1]]["pos"]
            ax.annotate(
                "",
                xy=end,
                xytext=start,
                arrowprops=dict(
                    arrowstyle="->",
                    color=dark_blue,
                    linewidth=1.4,
                    alpha=0.35,
                ),
                zorder=1,
            )

    for info in nodes.values():
        stage = info["stage"]
        x, y = info["pos"]
        scens = info["scens"]

        if stage == 0:
            facecolor = stage1_blue
        elif len(scens) > 1:
            facecolor = shared_grey
        else:
            facecolor = branch_grey

        ax.text(
            x,
            y,
            info["text"],
            ha="center",
            va="center",
            fontsize=9,
            zorder=5,
            bbox=dict(
                facecolor=facecolor,
                edgecolor=border_colour,
                boxstyle="round,pad=0.5",
                alpha=0.95,
            ),
        )

    for stage in range(n_stages):
        year = model.CONSTRUCTION_YEARS[stage]
        ax.text(
            stage * x_spacing,
            y_scenario[0] + y_space * 0.7,
            f"Stage {stage + 1}\n({year})",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            color=dark_blue,
        )

    ax.set_title(title, fontsize=16, fontweight="bold", pad=30)
    ax.set_xlim(-0.4, (n_stages - 1) * x_spacing + 0.4)
    ax.set_ylim(y_scenario[-1] - y_space * 1.5, y_scenario[0] + y_space * 1.2)

    plt.tight_layout()
    plt.show()

    return branches
