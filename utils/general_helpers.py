import numpy as np
CURRENCY = "$"


def money(value):
    """Format a number as money."""
    return f"{CURRENCY}{value:,.0f}"


def extract_pareto_arrays(pareto_records):
    """Pull the main Pareto values into separate arrays."""
    costs = np.array([r["cost"] for r in pareto_records])
    surplus_min = np.array([r["surplus_min"] for r in pareto_records])
    surplus_avg = np.array([r["surplus_avg"] for r in pareto_records])
    surplus_max = np.array([r["surplus_max"] for r in pareto_records])
    total_deficit = np.array([r["total_deficit"] for r in pareto_records])

    return costs, surplus_min, surplus_avg, surplus_max, total_deficit


def get_changed_pipes(x_matrix):
    """List which pipes changed at each stage."""
    x_matrix = np.asarray(x_matrix).astype(int)

    n_stages, n_pipes = x_matrix.shape
    previous = np.full(n_pipes, -1, dtype=int)
    notes = []

    for stage in range(n_stages):
        current = x_matrix[stage]
        changed = np.where(current != previous)[0]

        if stage == 0:
            notes.append(f"P1-P{n_pipes} (all)")
        elif len(changed) == 0:
            notes.append("No changes")
        else:
            notes.append(", ".join(f"P{p + 1}" for p in changed))

        previous = current.copy()

    return notes
