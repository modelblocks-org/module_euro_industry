# European Industrial Energy Demand Model

A modular workflow for preparing historical
European industrial production and energy-demand data, projecting
industrial production, applying process and production-route
transformations, spatially disaggregating national results.

------------------------------------------------------------------------

## 1. Main workflow

The model follows the sequence:

``` text
Raw data
   │
   ▼
Historical preparation
   │
   ├── historical production
   └── historical industrial energy demand
   │
   ▼
Production projection
   │
   ▼
Scenario transformations
   │
   ├── production-route changes
   ├── process transformations
   └── final industrial energy demand
   │
   ▼
Spatial disaggregation
   │
   ├── regional production
   └── regional energy demand
   │
   ▼
Visualization
```

The main user-facing execution sequence is:

``` bash
pixi run prepare
pixi run project-production
pixi run demand
pixi run spatial
pixi run plots
```

Because the workflow is managed by Snakemake, downstream tasks can also
trigger missing upstream dependencies automatically when the
corresponding rules are connected.

------------------------------------------------------------------------

## 2. Project structure

A typical project structure is:

``` text
.
├── config/
│   ├── config.yaml
│   ├── technologies.yaml
│   ├── visualization.yaml
│   └── scenarios/ # examples
│       ├── retain_max_electrification.yaml
│       └── industrial_relocation.yaml
│
├── resources/
│   ├── automatic/
│   │   ├── jrc_idees/
│   │   ├── eurostat/
│   │   ├── hotmaps.csv
│   │   └── ...
│   │
│   └── user/
│       ├── regions.geojson
│       ├── populations.csv
│       └── ...
│
├── results/
│   ├── historical/
│   ├── projections/
│   ├── demand/
│   ├── spatial/
│   ├── plots/
│   └── maps/
│
├── logs/
│
├── workflow/
│   ├── Snakefile
│   ├── rules/
│   │   ├── ...
│   │   ├── spatial.smk
│   │   └── visualizations.smk
│   │
│   ├── scripts/
│   │   ├── project_production.py
│   │   ├── build_spatial_distribution_keys.py
│   │   ├── disaggregate_industrial_data.py
│   │   ├── plot_results.py
│   │   ├── plot_spatial_maps.py
│   │   └── ...
│   │
│   ├── envs/
│   ├── internal/
│   └── profiles/
│
├── pixi.toml
└── README.md
```

------------------------------------------------------------------------

# 3. Environment and installation

## 3.1 Pixi

The project uses **Pixi** for environment and dependency management.

The environment should include the main packages required by the
workflow, including:

``` text
python
snakemake
pandas
numpy
pyyaml
openpyxl
pyxlsb
country_converter
geopandas
pyogrio
shapely
plotly
pydeck
```

The current workflow has been developed with Python 3.12 and Snakemake
9.

After cloning the repository, Pixi should create the environment
automatically when a task is executed.

For example:

``` bash
pixi run prepare
```
------------------------------------------------------------------------

# 4. Configuration philosophy

The configuration is intentionally divided into three conceptual layers.

## `config/config.yaml`

Defines the **general model setup** and data-processing settings.

Examples include:

-   historical reference year;
-   calibration assumptions;
-   active scenario;
-   technology-definition file;
-   spatial-disaggregation configuration;
-   spatial years;
-   region files;
-   fallback spatial keys.

## `config/technologies.yaml`

Defines **what technologies and production routes exist**.

This file should contain technological assumptions, not scenario
storylines.

Examples:

-   industrial heat pumps;
-   electric boilers;
-   electric furnaces;
-   hydrogen DRI;
-   EAF;
-   electrified HVC production;
-   route definitions and process intensities.

## `config/scenarios/<scenario>.yaml`

Defines **what changes under a scenario**.

Examples:

-   future production levels;
-   process transformations;
-   production-route shares;
-   commodity-specific production decline;
-   electrification schedules.

This separation is important:

``` text
technologies.yaml = what is technically available
scenario.yaml     = what happens in a particular future
```

------------------------------------------------------------------------

# 5. Main configuration

The main configuration points to the active technology and scenario
files.

Example:

``` yaml
technologies_file: config/technologies.yaml
scenario_file: config/scenarios/retain_max_electrification.yaml
```

Changing the active scenario therefore only requires changing:

``` yaml
scenario_file:
```

For example:

``` yaml
scenario_file: config/scenarios/industrial_relocation.yaml
```

------------------------------------------------------------------------

# 6. Historical calibration

Historical production and energy demand are prepared before scenario
assumptions are applied.

A typical calibration section is:

``` yaml
historical_calibration:
  reference_year: 2019

  basic_chemicals_without_NH3_production_today: 69.0
  HVC_production_today: 52.0
  chlorine_production_today: 9.58
  methanol_production_today: 1.5

  MWh_NH3_per_tNH3: 5.166
  MWh_H2_per_tNH3_electrolysis: 5.93
  MWh_elec_per_tNH3_electrolysis: 0.2473

  MWh_elec_per_tCl: 3.6
  MWh_H2_per_tCl: -0.9372

  MWh_elec_per_tMeOH: 0.167
  MWh_CH4_per_tMeOH: 10.25

  ammonia: true
  coke_oven_allocation: 0.75
```

These assumptions are used when the original datasets do not directly
provide all of the commodity-level information required by the model.

The historical preparation stage should therefore be treated as a
calibrated representation of the reference industrial system rather than
as a direct copy of a single source.

------------------------------------------------------------------------

# 7. Historical production

The historical preparation stage creates two main production files:

``` text
results/historical/production.csv
results/historical/production_aggregated.csv
```

## 7.1 Route-specific production

`production.csv` preserves production-route information where available.

Typical columns are:

``` text
country
sector
sector_name
activity
commodity
production_route
production
unit
year
source
source_field
```

Examples of explicit production routes include:

### Steel

``` text
STEEL
├── BF_BOF
└── EAF
```

### Aluminium

``` text
ALUMINIUM
├── PRIM_ALU
└── SEC_ALU
```

Industries without explicit route differentiation normally use:

``` text
BASE_ROUTE
```

## 7.2 Aggregated production

`production_aggregated.csv` aggregates route-specific production to
commodity level.

This is the primary input to the production-projection stage.

------------------------------------------------------------------------

# 8. Historical industrial energy demand

The historical industrial energy-demand output is:

``` text
results/historical/energy_demand.csv
```

The workflow intentionally preserves detailed JRC information instead of
immediately aggregating all fuels or processes.

Typical columns include:

``` text
country
year
sector
sector_name
activity
commodity
production_route
process
technology
carrier
energy_layer
use_type
demand
unit
source
subsector
jrc_process
jrc_energy_type
jrc_energy_carrier
source_description
source_sheet
source_value
source_unit
Code
source_note
```

This structure allows later transformations to operate on specific
processes while retaining provenance from the original data.

------------------------------------------------------------------------

# 9. FEC and UED

The workflow can retain both:

-   **FEC** --- Final Energy Consumption;
-   **UED** --- Useful Energy Demand.

They should not normally be summed together.

FEC describes energy entering the industrial process, while UED
represents the useful energy service after conversion efficiency.

For example, an industrial heat transformation can conceptually use UED
to determine the useful heat requirement and then calculate the
electricity required by a heat pump.

The visualization configuration therefore explicitly selects the energy
layer to display:

``` yaml
energy_layer: FEC
```

------------------------------------------------------------------------

# 10. Energy use types

Energy demand also distinguishes the purpose of energy or material use
through:

``` text
use_type
```

Important values include:

``` text
final_energy
feedstock
```

This prevents non-energy feedstock use from being silently mixed with
combustion or process-energy demand.

For chemical feedstocks where the source data do not provide a directly
coded UED equivalent, the historical preparation workflow may retain the
relevant FEC-based representation.

------------------------------------------------------------------------

# 11. Production projection

Future industrial production is projected from:

``` text
results/historical/production_aggregated.csv
```

and written to:

``` text
results/projections/production.csv
```

The basic relationship is:

``` text
future production
    =
reference-year production
    ×
projection factor
```

Projection factors are defined at anchor years and annual values between
anchor years are linearly interpolated.

------------------------------------------------------------------------

# 12. Generic production projections

The simplest scenario applies one projection trajectory to every
commodity and country.

Example:

``` yaml
production_projection:

  generic:
    2030: 1.0
    2040: 1.0
    2050: 1.0

  file: null
```

This means production remains equal to the reference-year level.

The reference year itself always has a projection factor of:

``` text
1.0
```

------------------------------------------------------------------------

# 13. Commodity-specific production projections

Commodity-specific projection curves can be defined directly in the
scenario YAML.

Example:

``` yaml
production_projection:

  generic:
    2030: 1.0
    2040: 1.0
    2050: 1.0

  commodities:

    STEEL:
      2030: 0.90
      2040: 0.70
      2050: 0.50

    HVC:
      2030: 0.90
      2040: 0.70
      2050: 0.50

  file: null
```

Here:

-   commodities without a specific curve follow `generic`;
-   `STEEL` follows the steel-specific trajectory;
-   `HVC` follows the HVC-specific trajectory.

The projection engine validates commodity names against historical
production so that misspelled or unknown commodity names do not silently
pass through the workflow.

------------------------------------------------------------------------

# 14. CSV production overrides

Country- and commodity-specific assumptions can still be supplied
through a CSV.

The expected structure is:

``` text
country,commodity,year,value
BE,STEEL,2040,0.60
DE,STEEL,2040,0.70
```

The scenario then points to the file:

``` yaml
production_projection:
  generic:
    2030: 1.0
    2040: 1.0
    2050: 1.0

  file: resources/user/production_projection.csv
```

The hierarchy is:

``` text
generic YAML
      ↓
commodity-specific YAML
      ↓
country/commodity CSV
```

Therefore the most specific assumption wins.

This makes it possible to define broad scenario assumptions in YAML
while retaining the option to specify detailed national trajectories
externally.

------------------------------------------------------------------------

# 15. Industrial relocation test scenario

A simple industrial-relocation/deindustrialization stress test can be
represented by reducing selected European commodities.

For example:

``` yaml
production_projection:

  generic:
    2030: 1.0
    2040: 1.0
    2050: 1.0

  commodities:

    STEEL:
      2030: 0.90
      2040: 0.70
      2050: 0.50

    HVC:
      2030: 0.90
      2040: 0.70
      2050: 0.50

    AMMONIA:
      2030: 0.90
      2040: 0.70
      2050: 0.50

    METHANOL:
      2030: 0.90
      2040: 0.70
      2050: 0.50

    CHLORINE:
      2030: 0.90
      2040: 0.70
      2050: 0.50

  file: null
```

All other commodities remain at 100% of reference production.

### Important interpretation

This scenario represents production **leaving the modeled European
industrial system**.

It does not currently determine where the lost production relocates.

Therefore:

``` text
European production decreases
≠
the model endogenously relocates production elsewhere
```

A future extension could explicitly allocate the lost production to
other countries or world regions.

------------------------------------------------------------------------

# 16. Technology definitions

Technologies and routes are defined in:

``` text
config/technologies.yaml
```

Example process definitions:

``` yaml
processes:

  industrial_heat_pump:
    efficiency: 3.0
    carriers:
      ELEC:
        share: 1.0

  electric_boiler:
    efficiency: 0.98
    carriers:
      ELEC:
        share: 1.0

  electric_furnace:
    efficiency: 0.95
    carriers:
      ELEC:
        share: 1.0

  hydrogen_dri:
    intensities:
      HYDROGEN: 1.80
      ELEC: 0.10

  new_eaf:
    intensities:
      ELEC: 0.65

  electric_hvc_conversion:
    intensities:
      ELEC: 2.00
```

Two types of technology representation are therefore possible:

### Efficiency-based processes

Useful for energy-service substitutions such as heat:

``` yaml
efficiency: 3.0
carriers:
  ELEC:
    share: 1.0
```

### Production-intensity processes

Useful for new industrial routes:

``` yaml
intensities:
  HYDROGEN: 1.80
  ELEC: 0.10
```

------------------------------------------------------------------------

# 17. Production routes

New production routes can combine multiple processes.

Example:

``` yaml
production_routes:

  H2_DRI_EAF:
    commodity: STEEL
    processes:
      - hydrogen_dri
      - new_eaf

  ELECTRIC_HVC:
    commodity: HVC
    inherit_use_types_from:
      production_route: BASE_ROUTE
      use_types:
        - feedstock
    processes:
      - electric_hvc_conversion
```

The H2-DRI-EAF route therefore combines:

``` text
hydrogen_dri
+
new_eaf
```

The HVC example demonstrates feedstock inheritance.

This is useful when a new route changes process energy demand but should
retain feedstock demand from an existing route.

------------------------------------------------------------------------

# 18. Process transformations

Process transformations modify existing industrial processes.

They are defined in the scenario rather than in `technologies.yaml`.

A transformation can target:

``` text
country
commodity
production_route
process
year
```

Wildcard selectors are supported.

For example:

``` yaml
commodity: "*"
production_route: "*"
process: LOW_ENTHALPY_HEAT
```

means:

> apply the transformation to every commodity and production route where
> `LOW_ENTHALPY_HEAT` actually exists.

The transformation engine does not invent a process for groups where the
historical process is absent.

If a matched group has no positive useful-energy demand for the selected
process, the transformation is skipped and the historical rows are
retained.

This avoids failures caused by structurally valid selectors that happen
to encounter zero-demand groups.

------------------------------------------------------------------------

# 19. Production-route shares

Scenarios can define future route shares independently of the total
production projection.

Example for steel:

``` yaml
route_shares:

  STEEL:

    BF_BOF:
      2030: 0.55
      2040: 0.20
      2050: 0.00

    EAF:
      2030: 0.35
      2040: 0.40
      2050: 0.45

    H2_DRI_EAF:
      2030: 0.10
      2040: 0.40
      2050: 0.55
```

The conceptual separation is:

``` text
production_projection
        ↓
How much STEEL is produced?

route_shares
        ↓
How is that STEEL produced?
```

This distinction is important.

A scenario can therefore independently change:

1.  total industrial output; and
2.  the technology used to produce that output.

------------------------------------------------------------------------

# 20. Transformation outputs

The transformation stage creates:

``` text
results/demand/route_production.csv
results/demand/industrial_energy_demand.csv
```

## `route_production.csv`

Contains production allocated to individual production routes.

Conceptually:

``` text
commodity production
×
route share
=
route production
```

## `industrial_energy_demand.csv`

Contains the resulting industrial energy demand after applying:

-   projected production;
-   route allocation;
-   historical process structure;
-   process transformations;
-   new production routes;
-   technology efficiencies;
-   carrier requirements;
-   feedstock inheritance.

------------------------------------------------------------------------

# 21. Spatial disaggregation

The national industrial results can be disaggregated to user-defined
regions.

The spatial workflow uses:

``` text
resources/user/regions.geojson
```

The GeoJSON can represent any desired regional structure as long as the
configured region and country identifiers are available.

Example configuration:

``` yaml
spatial_disaggregation:

  regions_file: resources/user/regions.geojson
  region_id_column: name
  country_column: country

  years:
    - 2030
    - 2040
    - 2050

  fallback_options:
    - generic_industry
    - population
    - user_key
    - uniform
```

Only the selected years are spatially expanded.

This is important because the national model may contain annual results,
while expanding every annual row to every region can create
unnecessarily large spatial CSV files.

Setting:

``` yaml
years: null
```

allows all available years to be spatialized.

------------------------------------------------------------------------

# 22. Spatial distribution keys

The workflow first builds:

``` text
results/spatial/industrial_distribution_keys.csv
```

These keys determine what fraction of a country's industrial activity is
assigned to each region.

The primary spatial information comes from sector-specific Hotmaps
industrial sites.

A simplified conceptual hierarchy is:

``` text
sector-specific Hotmaps sites
          ↓
generic industrial Hotmaps sites
          ↓
population key
          ↓
user-defined key
          ↓
uniform distribution
```

The actual fallback order is controlled by:

``` yaml
fallback_options:
```

------------------------------------------------------------------------

# 23. Spatial fallback methods

## `generic_industry`

Uses all available Hotmaps industrial sites within the country when no
suitable sector-specific sites are available.

## `population`

Uses a user-provided regional population weighting file.

Example:

``` yaml
population:
  file: resources/user/pop_layout_base_s_60.csv
  region_column: name
  country_column: ct
  weight_column: fraction
```

## `user_key`

Allows any externally prepared regional weighting key.

Example:

``` yaml
user_key:
  file: null
  region_column: region
  country_column: country
  weight_column: share
  source_name: user_key
```

## `uniform`

Splits national activity equally across all model regions belonging to
the country.

This should normally be considered the last fallback.

------------------------------------------------------------------------

# 24. Spatial key provenance

The generated spatial keys retain information about how each
distribution was obtained.

Typical values include:

``` text
hotmaps_subsector
generic_industry
population
user_key
uniform
```

This is important for diagnostics.

A result spatialized using sector-specific industrial locations has a
different evidence basis from one distributed uniformly across a
country.

------------------------------------------------------------------------

# 25. Commodity-to-Hotmaps mapping

Industrial commodities are mapped to broader Hotmaps industrial
categories.

Examples include:

``` text
STEEL
→ Iron and steel

HVC / chemical commodities
→ Chemical industry

CEM
→ Cement

GLASS
→ Glass

PAPER / PULP / PRINT
→ Paper and printing

ALUMINIUM / ALUMINA
→ Non-ferrous metals

other non-metallic minerals
→ Non-metallic mineral products
```

Other industries can fall back to broader non-classified industrial
categories where appropriate.

------------------------------------------------------------------------

# 26. Spatial outputs

The spatial workflow creates:

``` text
results/spatial/industrial_distribution_keys.csv
results/spatial/industrial_energy_demand.csv
results/spatial/route_production.csv
```

The national totals should be conserved during spatial disaggregation:

``` text
sum(regional values within country)
=
national value
```

This conservation should be checked whenever the spatial logic is
modified.

------------------------------------------------------------------------

# 27. Important spatial-model limitation

The current spatial module is a **disaggregation model**, not a spatial
optimization model.

It answers:

> Given national industrial production and energy demand, where should
> that activity be represented spatially?

It does not answer:

> In which European region should future industry optimally locate?

New production routes inherit the geography of their associated
commodity unless additional relocation assumptions are explicitly
introduced.

Similarly, process transformations change technology and energy demand
but do not automatically relocate an industrial facility.

------------------------------------------------------------------------

# 28. Visualization

Visualization settings are kept in one file:

``` text
config/visualization.yaml
```

This controls both:

-   non-spatial Plotly figures;
-   spatial PyDeck maps.

Example:

``` yaml
visualization:

  countries: null
  commodities: null

  production:
    make_overview: false
    make_route_plots: false

  energy:
    make_carrier_plot: false
    make_commodity_plot: false
    energy_layer: FEC
    use_type: final_energy

  output_dir: results/plots

  spatial_maps:
    enabled: true
    years: null
    output_dir: results/maps

    plots:
      production_maps: true
      energy_by_sector_pies: true
      energy_by_commodity_pies: false
      energy_by_carrier_pies: false
```

This makes it possible to generate only the figures needed for a
particular analysis.

------------------------------------------------------------------------

# 29. Non-spatial Plotly figures

Available plot types include:

## Production overview

``` yaml
production:
  make_overview: true
```

Shows projected production as an index:

``` text
reference year = 100
```

This makes commodities with different physical units easier to compare.

## Production by route

``` yaml
production:
  make_route_plots: true
```

Creates route-specific production plots for commodities with multiple
active routes.

## Energy demand by carrier

``` yaml
energy:
  make_carrier_plot: true
```

## Energy demand by commodity

``` yaml
energy:
  make_commodity_plot: true
```

The energy plots can be filtered by:

``` yaml
energy_layer: FEC
use_type: final_energy
```

Outputs are written to:

``` text
results/plots/
```

unless another directory is configured.

------------------------------------------------------------------------

# 30. Spatial production maps

Production maps are enabled with:

``` yaml
spatial_maps:
  plots:
    production_maps: true
```

A separate interactive HTML map is generated for each selected:

``` text
commodity × year
```

Production is shown as a regional choropleth.

Tooltips can include production-route information so that both total
production and its technological composition can be inspected.

The output naming follows the pattern:

``` text
production_<commodity>_<year>.html
```

------------------------------------------------------------------------

# 31. Spatial energy-demand pie maps

Regional energy-demand maps can show pie charts whose:

``` text
pie size   = total regional energy demand
pie slices = composition
```

Composition can be selected as:

``` yaml
energy_by_sector_pies: true
energy_by_commodity_pies: false
energy_by_carrier_pies: false
```

For example, the sector map answers:

> How large is industrial energy demand in each region, and which
> industrial sectors account for it?

------------------------------------------------------------------------

# 32. Pie-chart sizing

The current simplified map logic scales pie radius approximately as:

``` text
radius
=
sqrt(regional demand / maximum regional demand)
×
pie_radius_factor
```

This means pie **area** is approximately proportional to regional
demand.

Example:

``` yaml
pie_radius_factor: 0.45
```

A smaller value produces smaller pies:

``` yaml
pie_radius_factor: 0.25
```

A larger value produces larger pies:

``` yaml
pie_radius_factor: 0.65
```

The pies are rendered as geographic wedges rather than fixed screen
icons, so they behave as map objects during zooming.

To avoid unreadable pies with many categories:

``` yaml
max_pie_slices: 10
```

can be used. Smaller categories beyond the configured limit are grouped
into `OTHER`.

------------------------------------------------------------------------

# 33. Selecting spatial years

By default:

``` yaml
spatial_maps:
  years: null
```

means the visualization uses the years selected under:

``` yaml
spatial_disaggregation:
  years:
```

A separate list can be supplied under `spatial_maps.years` if only a
subset of the spatialized years should be visualized.

------------------------------------------------------------------------

# 34. Running the workflow

## Step 1 --- prepare historical data

``` bash
pixi run prepare
```

Expected main outputs:

``` text
results/historical/production.csv
results/historical/production_aggregated.csv
results/historical/energy_demand.csv
```

## Step 2 --- project industrial production

``` bash
pixi run project-production
```

Expected output:

``` text
results/projections/production.csv
```

## Step 3 --- transform industrial demand

``` bash
pixi run demand
```

Expected outputs:

``` text
results/demand/route_production.csv
results/demand/industrial_energy_demand.csv
```

## Step 4 --- spatialize

``` bash
pixi run spatial
```

Expected outputs:

``` text
results/spatial/industrial_distribution_keys.csv
results/spatial/route_production.csv
results/spatial/industrial_energy_demand.csv
```

## Step 5 --- create plots and maps

``` bash
pixi run plots
```

Expected output directories:

``` text
results/plots/
results/maps/
```

------------------------------------------------------------------------

# 35. Recommended scenario workflow

When creating a new scenario:

### 1. Copy an existing scenario

For example:

``` text
config/scenarios/retain_max_electrification.yaml
```

to:

``` text
config/scenarios/my_scenario.yaml
```

### 2. Define production assumptions

``` yaml
production_projection:
```

### 3. Define process transformations

``` yaml
process_transformations:
```

### 4. Define route shares

``` yaml
route_shares:
```

### 5. Point the model to the scenario

In:

``` text
config/config.yaml
```

set:

``` yaml
scenario_file: config/scenarios/my_scenario.yaml
```

### 6. Rerun the relevant workflow

At minimum:

``` bash
pixi run project-production
pixi run demand
pixi run spatial
pixi run plots
```

------------------------------------------------------------------------

# 36. Adding a new technology

A new technology should normally be added to:

``` text
config/technologies.yaml
```

For example:

``` yaml
processes:

  my_new_process:
    efficiency: 0.95
    carriers:
      ELEC:
        share: 1.0
```

or:

``` yaml
processes:

  my_new_process:
    intensities:
      ELEC: 0.8
      HYDROGEN: 1.2
```

The scenario can then decide when and where the technology is used.

Do not hard-code scenario adoption assumptions inside the technology
definition.

------------------------------------------------------------------------

# 37. Adding a new production route

Define the processes first:

``` yaml
processes:
  process_a:
    ...

  process_b:
    ...
```

Then define the route:

``` yaml
production_routes:

  NEW_ROUTE:
    commodity: MY_COMMODITY
    processes:
      - process_a
      - process_b
```

Finally, activate it in a scenario:

``` yaml
route_shares:

  MY_COMMODITY:

    BASE_ROUTE:
      2030: 0.8
      2050: 0.2

    NEW_ROUTE:
      2030: 0.2
      2050: 0.8
```

------------------------------------------------------------------------

# 38. Adding a new spatial fallback

The spatial-distribution system is intentionally hierarchical.

A new fallback should:

1.  provide regional weights;
2.  identify country and region;
3.  normalize weights within the relevant national group;
4.  preserve national totals;
5.  record its source in the spatial-key output.

The fallback should then be added to the configured:

``` yaml
fallback_options:
```

rather than silently replacing an existing method.

------------------------------------------------------------------------

# 39. Data validation

Several consistency checks are particularly important.

## Production conservation

For each country, commodity, and year:

``` text
sum(route production)
≈
projected commodity production
```

## Route shares

For commodities with route transformations:

``` text
sum(route shares)
≈
1
```

## Spatial conservation

For each national observation:

``` text
sum(regional values)
≈
national value
```

## Projection factors

Projection factors must be:

``` text
finite
and
>= 0
```

## Commodity names

Scenario commodity names should match commodities present in the
historical production dataset.

## Energy layers

Do not aggregate FEC and UED as if they represented independent energy
quantities.

## Feedstock

Do not automatically combine feedstock demand with final-energy demand
unless that is explicitly intended for the analysis.

------------------------------------------------------------------------

# 40. Logs and debugging

Rule logs are stored under:

``` text
logs/
```

Examples include:

``` text
logs/spatial/build_industrial_distribution_keys.log
logs/spatial/disaggregate_industrial_energy_demand.log
logs/spatial/disaggregate_route_production.log
logs/plots/plot_results.log
logs/plots/plot_spatial_maps.log
```

When a Snakemake rule fails, inspect its log before rerunning the script
manually.

A useful workflow is:

``` bash
pixi run <task>
```

then inspect the corresponding file under:

``` text
logs/
```

------------------------------------------------------------------------

# 41. Common issues

## Unknown commodity in a scenario

If a commodity-specific production projection refers to a commodity not
present in historical production, check the exact commodity name.

For example:

``` yaml
STEEL:
```

is different from:

``` yaml
Steel:
```

unless explicit normalization has been implemented.

------------------------------------------------------------------------

## Spatial country missing from the GeoJSON

The spatial workflow can only regionalize countries represented by the
supplied region geometry.

Countries included in national results but outside the GeoJSON spatial
scope should be skipped rather than arbitrarily assigned to another
region.

------------------------------------------------------------------------

## Missing sector-specific Hotmaps sites

The spatial key builder moves through the configured fallback hierarchy.

Check:

``` text
spatial_key_source
```

to determine which method was ultimately used.

------------------------------------------------------------------------

## Very large spatial CSV files

Restrict:

``` yaml
spatial_disaggregation:
  years:
```

to the years required for spatial analysis.

For example:

``` yaml
years:
  - 2030
  - 2040
  - 2050
```

------------------------------------------------------------------------

## Too many maps

Disable unwanted maps in:

``` text
config/visualization.yaml
```

For example:

``` yaml
plots:
  production_maps: true
  energy_by_sector_pies: true
  energy_by_commodity_pies: false
  energy_by_carrier_pies: false
```

------------------------------------------------------------------------

## Pie charts too large or too small

Adjust only:

``` yaml
pie_radius_factor:
```

For example:

``` yaml
pie_radius_factor: 0.30
```

The square-root scaling already handles differences in regional demand.

------------------------------------------------------------------------

# 42. Current conceptual boundaries

The model currently focuses on **industrial production and industrial
energy demand**.

It is not currently intended to be:

-   a full energy-system optimization model;
-   an industrial plant investment optimization model;
-   an endogenous industrial-location model;
-   a CGE model;
-   a trade model;
-   or an endogenous commodity-price model.

Instead, it creates transparent industrial-demand scenarios that can
subsequently be coupled to energy-system models.

This separation is deliberate.

------------------------------------------------------------------------

# 43. Potential future extensions

Possible extensions include:

-   explicit relocation between European countries;
-   relocation from Europe to external regions;
-   endogenous industrial-location optimization;
-   material recycling scenarios;
-   circularity and material-demand reduction;
-   carbon capture and storage;
-   carbon capture and utilization;
-   process emissions;
-   biomass feedstock constraints;
-   industrial hydrogen infrastructure;
-   industrial electricity-grid constraints;
-   technology cost trajectories;
-   endogenous technology choice;
-   industrial trade;
-   scenario comparison dashboards;
-   uncertainty and sensitivity analysis.

------------------------------------------------------------------------

# 44. Reproducibility principles

The workflow follows several principles intended to make scenario
results auditable.

### Preserve source detail

Historical carrier, process, route, and provenance information should be
retained whenever possible.

### Separate data from assumptions

Historical preparation should not contain future scenario choices.

### Separate technology definitions from scenario adoption

`technologies.yaml` defines what exists.

Scenario YAML files define what is used.

### Keep transformations explicit

A future energy-demand change should be traceable to:

``` text
production change
route change
process change
or technology assumption
```

### Preserve spatial provenance

Regional results should identify whether their spatial allocation came
from:

``` text
Hotmaps
generic industry
population
user key
or uniform fallback
```

------------------------------------------------------------------------

# 45. Quick-start example

To run the existing model:

``` bash
pixi run prepare
pixi run project-production
pixi run demand
pixi run spatial
pixi run plots
```

To test the industrial-relocation scenario, change:

``` yaml
scenario_file: config/scenarios/industrial_relocation.yaml
```

and rerun:

``` bash
pixi run project-production
pixi run demand
pixi run spatial
pixi run plots
```

The resulting production trajectory can then be inspected in:

``` text
results/projections/production.csv
```

the transformed industrial demand in:

``` text
results/demand/industrial_energy_demand.csv
```

and regional results in:

``` text
results/spatial/
```

------------------------------------------------------------------------

# 46. Summary

The workflow can be summarized as:

``` text
Historical industrial data
        │
        ▼
Reference production + energy demand
        │
        ▼
Production scenario
        │
        ▼
Production-route allocation
        │
        ▼
Process and technology transformations
        │
        ▼
Industrial energy demand
        │
        ▼
Spatial disaggregation
        │
        ▼
Interactive plots and maps
```

The central design principle is to keep **historical evidence**,
**technology definitions**, **scenario assumptions**, **spatial
assumptions**, and **visualization choices** separate.

This makes the workflow suitable for developing transparent and
reproducible European industrial transition scenarios while retaining
enough process, carrier, route, and spatial detail for later integration
with energy-system analysis.
