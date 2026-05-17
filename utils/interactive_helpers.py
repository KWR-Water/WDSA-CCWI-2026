import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
try:
    from general_helpers import CURRENCY, extract_pareto_arrays
except Exception:
    CURRENCY = "$"


def run_interactive_pareto_explorer(pareto_records):
    """Show sliders for budget and worst-case pressure surplus."""
    import ipywidgets as widgets
    from IPython.display import display

    if len(pareto_records) == 0:
        print("No Pareto records available.")
        return

    costs, surplus_min, surplus_avg, surplus_max, total_deficit = extract_pareto_arrays(
        pareto_records
    )

    budget_slider = widgets.FloatSlider(
        value=np.percentile(costs, 85),
        min=np.min(costs),
        max=np.max(costs),
        step=10_000,
        description="Max Budget:",
        readout_format=",.0f",
        layout={"width": "600px"},
    )

    surplus_slider = widgets.FloatSlider(
        value=0.0,
        min=np.floor(np.min(surplus_min)),
        max=np.ceil(np.max(surplus_min)),
        step=0.5,
        description="Min Surplus:",
        layout={"width": "600px"},
    )

    def update_dashboard(max_budget, min_surplus):
        warnings.filterwarnings("ignore", category=ImportWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        valid = (costs <= max_budget) & (surplus_min >= min_surplus)
        valid_idx = np.where(valid)[0]

        fig, ax = plt.subplots(figsize=(11, 5.5))

        dark_blue = "#1f4e79"
        mid_blue = "#5b9bd5"
        light_blue = "#d9eaf7"

        # Full Pareto range.
        ax.fill_between(
            costs,
            surplus_min,
            surplus_max,
            color=light_blue,
            alpha=0.65,
            label="Scenario range",
        )
        ax.plot(
            costs,
            surplus_min,
            "o-",
            color=dark_blue,
            linewidth=2.2,
            markersize=5,
            alpha=0.30,
            label="Worst-case surplus",
        )
        ax.plot(
            costs,
            surplus_avg,
            ".-",
            color=mid_blue,
            linewidth=1.3,
            markersize=4,
            alpha=0.55,
            label="Average surplus",
        )
        ax.plot(
            costs,
            surplus_max,
            "o--",
            color=dark_blue,
            linewidth=1.4,
            markersize=4,
            alpha=0.30,
            label="Best-case surplus",
        )

        # Highlight the solutions that pass both slider filters.
        if len(valid_idx) > 0:
            ax.plot(
                costs[valid_idx],
                surplus_min[valid_idx],
                "o-",
                color=dark_blue,
                linewidth=2.5,
                markersize=8,
                label="Valid solutions",
            )

        ax.axhline(
            0,
            color="black",
            linewidth=1.1,
            alpha=0.45,
            label="Feasibility boundary",
        )
        ax.axvline(
            max_budget,
            color="red",
            linestyle=":",
            linewidth=2,
            label="Selected budget",
        )
        ax.axhline(
            min_surplus,
            color="green",
            linestyle=":",
            linewidth=2,
            label="Selected surplus",
        )

        ax.set_title(
            f"Interactive Pareto Explorer: {len(valid_idx)} valid pathways found",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel(f"Total discounted cost — NPV ({CURRENCY})")
        ax.set_ylabel("Minimum pressure surplus (m)")
        ax.xaxis.set_major_formatter(StrMethodFormatter(f"{CURRENCY}" + "{x:,.0f}"))
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=9, loc="lower right")

        plt.tight_layout()
        plt.show()

        if len(valid_idx) == 0:
            print("⚠ No solutions meet your criteria.")
            return

        results = pd.DataFrame({
            "Idx": valid_idx,
            f"Cost ({CURRENCY})": costs[valid_idx],
            "Worst-case minimum surplus": surplus_min[valid_idx],
            "Best-case minimum surplus": surplus_max[valid_idx],
            "Total deficit": total_deficit[valid_idx],
        })

        display(
            results.style
            .hide(axis="index")
            .format({
                f"Cost ({CURRENCY})": CURRENCY + "{:,.0f}",
                "Worst-case minimum surplus": "{:.2f} m",
                "Best-case minimum surplus": "{:.2f} m",
                "Total deficit": "{:.2f}",
            })
        )

    ui = widgets.VBox([budget_slider, surplus_slider])
    out = widgets.interactive_output(
        update_dashboard,
        {"max_budget": budget_slider, "min_surplus": surplus_slider},
    )

    display(ui, out)
