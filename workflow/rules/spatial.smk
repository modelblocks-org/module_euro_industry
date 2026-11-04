regions_file = config["spatial_disaggregation"]["regions_file"]

population_file = config["spatial_disaggregation"]["population"]["file"]
user_key_file = config["spatial_disaggregation"]["user_key"]["file"]

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
        distribution_keys="results/spatial/industrial_distribution_keys.parquet",
    log:
        "logs/spatial/build_industrial_distribution_keys.log",
    conda:
        "../envs/module.yaml"
    params:
        region_id_column=config["spatial_disaggregation"]["region_id_column"],
        country_column=config["spatial_disaggregation"]["country_column"],
        fallback_options=config["spatial_disaggregation"]["fallback_options"],
        population_region_column=config["spatial_disaggregation"]["population"][
            "region_column"
        ],
        population_country_column=config["spatial_disaggregation"]["population"][
            "country_column"
        ],
        population_weight_column=config["spatial_disaggregation"]["population"][
            "weight_column"
        ],
        population_source_name=config["spatial_disaggregation"]["population"][
            "source_name"
        ],
        user_key_region_column=config["spatial_disaggregation"]["user_key"][
            "region_column"
        ],
        user_key_country_column=config["spatial_disaggregation"]["user_key"][
            "country_column"
        ],
        user_key_weight_column=config["spatial_disaggregation"]["user_key"][
            "weight_column"
        ],
        user_key_source_name=config["spatial_disaggregation"]["user_key"]["source_name"],
    script:
        "../scripts/build_spatial_distribution_keys.py"


rule disaggregate_industrial_energy_demand:
    input:
        data="results/demand/industrial_energy_demand.parquet",
        distribution_keys=rules.build_industrial_distribution_keys.output.distribution_keys,
    output:
        data="results/spatial/industrial_energy_demand.parquet",
    log:
        "logs/spatial/disaggregate_industrial_energy_demand.log",
    conda:
        "../envs/module.yaml"
    params:
        value_column="demand",
        years=config["spatial_disaggregation"]["years"],
    script:
        "../scripts/disaggregate_industrial_data.py"


rule disaggregate_route_production:
    input:
        data="results/demand/route_production.parquet",
        distribution_keys=rules.build_industrial_distribution_keys.output.distribution_keys,
    output:
        data="results/spatial/route_production.parquet",
    log:
        "logs/spatial/disaggregate_route_production.log",
    conda:
        "../envs/module.yaml"
    params:
        value_column="route_production",
        years=config["spatial_disaggregation"]["years"],
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
