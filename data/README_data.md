# Data

The input data file `pww_sdm_input_data.xlsx` is archived at:

**Zenodo: https://doi.org/10.5281/zenodo.20369405**

A byte-identical copy is committed here, so no download is needed.

This file is shared with the companion repository
[olesonlab/puuwaawaa-sdm](https://github.com/olesonlab/puuwaawaa-sdm),
which contains the base optimization code. The normalization analysis
in this repository applies alternative scoring methods to the same input data.

## Contents of pww_sdm_input_data.xlsx

| Sheet | Description |
|-------|-------------|
| `paddock_data` | Paddock identifiers, elevation zones, areas (m²), and per-paddock per-alternative costs for Alternatives 1–11. Column E (index 4) is a spacer column preserving the column offsets expected by the optimizer. |
| `native_rareplants` | Native forest cover (%) and T&E plant counts per paddock. Data begin at row 5 (pandas index 4) to preserve row offsets expected by the optimizer. |
| `People` | Expert-elicited community preference base scores for recreationists (cols C–M), hunters (cols P–Z), and ranchers (cols AC–AM) per alternative. Spacer columns at N–O and AA–AB preserve column offsets expected by the optimizer. |
| `flammability` | Baseline Q3 fire probability per paddock (col B) and post-management fire probability per paddock per alternative (cols F–P). Spacer columns at D–E preserve column offsets expected by the optimizer. Data begin at row 5 (pandas index 4). |
| `alternatives_reference` | Reference table describing each of the 11 management alternatives. Not read by the optimizer. |

## Notes on spacer columns and row offsets

The optimizer reads data using hardcoded `iloc` indices. The spacer columns and extra header rows in `pww_sdm_input_data.xlsx` are intentional: they preserve the exact column and row offsets the optimizer expects. Do not remove them.

The shared fuelbreak cost (`shared_firebreak_cost = 80,728.08`) is hardcoded in the optimizer and is noted in the `paddock_data` sheet header for reference.

## Data provenance

Paddock boundaries and ecological data derive from DOFAW spatial databases
and the Puʻuwaʻawaʻa management plan (DLNR 2003).

T&E plant counts were compiled by DOFAW from systematic surveys
(Balzotti et al. 2017/2020; DLNR 2003).

Fire probability estimates derive from the spatially explicit fire model
of Trauernicht (2019).

Community preference scores were expert-elicited from DOFAW managers
(co-authors EP, and collaborators) during a 2018 rapid-prototyping workshop.

Costs represent mean estimates from contractor bids and DOFAW records.
