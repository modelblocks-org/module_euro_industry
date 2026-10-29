spatial_cfg = config["spatial_disaggregation"]
regions_file = spatial_cfg["regions_file"]

population_file = spatial_cfg.get("population", {}).get("file")
user_key_file = spatial_cfg.get("user_key", {}).get("file")

spatial_key_inputs = {
    "regions": regions_file,
    "hotmaps": "resources/automatic/hotmaps.csv",
}
if population_file:
    spatial_key_inputs["population"] = population_file
if user_key_file:
    spatial_key_inputs["user_key"] = user_key_file


rule build_industrial_distribution_keys:
    input:
        **spatial_key_inputs,
    output:
        "results/spatial/industrial_distribution_keys.parquet",
    log:
        "logs/spatial/build_industrial_distribution_keys.log",
    conda:
        "../envs/module.yaml"
    params:
        config_path="config/config.yaml",
    script:
        "../scripts/build_spatial_distribution_keys.py"


rule disaggregate_industrial_energy_demand:
    input:
        data="results/demand/industrial_energy_demand.parquet",
        distribution_keys=rules.build_industrial_distribution_keys.output[0],
        config="config/config.yaml",
    output:
        "results/spatial/industrial_energy_demand.parquet",
    log:
        "logs/spatial/disaggregate_industrial_energy_demand.log",
    conda:
        "../envs/module.yaml"
    params:
        value_column="demand",
    script:
        "../scripts/disaggregate_industrial_data.py"


rule disaggregate_route_production:
    input:
        data="results/demand/route_production.parquet",
        distribution_keys=rules.build_industrial_distribution_keys.output[0],
        config="config/config.yaml",
    output:
        "results/spatial/route_production.parquet",
    log:
        "logs/spatial/disaggregate_route_production.log",
    conda:
        "../envs/module.yaml"
    params:
        value_column="route_production",
    script:
        "../scripts/disaggregate_industrial_data.py"


rule spatial_all:
    input:
        rules.disaggregate_industrial_energy_demand.output,
        rules.disaggregate_route_production.output,
    output:
        touch("results/spatial/.spatial_complete"),
    conda:
        "../envs/module.yaml"
