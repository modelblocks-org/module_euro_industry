"""Future industrial route and process transformation layer."""

technologies_file = config["technologies_file"]
scenario_file = config["scenario_file"]


rule transform_industrial_demand:
    input:
        projected_production="results/projections/production.parquet",
        historical_production="results/historical/production.parquet",
        historical_energy="results/historical/energy_demand.parquet",
        technologies=technologies_file,
        scenario=scenario_file,
    output:
        demand="results/demand/industrial_energy_demand.parquet",
        route_production="results/demand/route_production.parquet",
    log:
        "logs/demand/transform_industrial_demand.log",
    conda:
        "../envs/module.yaml"
    params:
        config_path="config/config.yaml",
    script:
        "../scripts/transform_industrial_demand.py"


rule demand_all:
    input:
        rules.transform_industrial_demand.output,
    output:
        touch("results/demand/.demand_complete"),
    conda:
        "../envs/module.yaml"
