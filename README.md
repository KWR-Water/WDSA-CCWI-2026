# WDSA/CCWI 2026 - Short Course SC1
## From Best-Guess to Better Decisions: Modern Optimisation for Water Distribution Systems

**Paphos, Cyprus, 18 May 2026**

Authors
* Dragan Savić
* Lydia Tsiami
* Mark Morley
* Christos Michalopoulos
* Dennis Zanutto

---

## Agenda

Put the agenda here

## Repository Structure

```
├── networks/          # EPANET .inp network files used in the notebooks
│                      # (networks already included in EPyT are not duplicated here)
├── notebooks/         # One Jupyter notebook per course part
│   ├── part1_intro_to_optimisation.ipynb
│   ├── part2_robust_flexible_staged.ipynb
│   └── part3_design_and_operations.ipynb
└── presentations/     # Slide decks in PDF format
```

## Dependencies

The notebooks rely on two main libraries:

- **[EPyT](https://github.com/OpenWaterAnalytics/EPyT)** — EPANET Python Toolkit. Provides a Python interface to the EPANET hydraulic simulator, used throughout for network loading, simulation, and result extraction.
- **[pygmo](https://esa.github.io/pygmo2/)** — Parallel Global Multiobjective Optimiser. Provides the optimisation algorithms and the population/island infrastructure used for all optimisation runs.

## Getting Started

```bash
# Clone the repository
git clone https://github.com/KWR-Water/WDSA-CCWI-2026-SC1.git
cd WDSA-CCWI-2026-SC1

# Create and activate a conda environment
conda create -n wdsa-sc1 python=3.11.11
conda activate wdsa-sc1

# Install pygmo via conda (recommended to avoid compiler issues)
conda install -c conda-forge pygmo

# Install remaining dependencies via pip
pip install epyt jupyter

# Launch the notebooks
jupyter notebook notebooks/
```

> **Note:** pygmo installation require a C++ compiler on some platforms, installing via conda is the simplest way. 

> **Running on Google Colab?** Add the following two cells at the top of the notebook before any imports:
> 
> ```python
> # Install conda on Colab (required to build pygmo)
> !python --version
> !pip install condacolab
> import condacolab
> condacolab.install()
> ```
> 
> ```python
> # Install dependencies
> !python --version
> !conda install pygmo
> !pip install epyt
> ```
> 
> Note that `condacolab.install()` will restart the Colab runtime — this is expected. Run the second cell after the restart completes.