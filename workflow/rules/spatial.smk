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

population_arg = f'--population "{population_file}"' if population_file else ""
user_key_arg = f'--user-key "{user_key_file}"' if user_key_file else ""

rule build_industrial_distribution_keys:
    input:
        **spatial_key_inputs
    output:
        "results/spatial/industrial_distribution_keys.csv"
    log:
        "logs/spatial/build_industrial_distribution_keys.log"
    params:
        population_arg=population_arg,
        user_key_arg=user_key_arg,
    shell:
        (
            'python workflow/scripts/build_spatial_distribution_keys.py '
            '--config "config/config.yaml" '
            '--regions "{input.regions}" '
            '--hotmaps "{input.hotmaps}" '
            '{params.population_arg} '
            '{params.user_key_arg} '
            '--output "{output}" '
            '> "{log}" 2>&1'
        )


rule disaggregate_industrial_energy_demand:
    input:
        demand="results/demand/industrial_energy_demand.csv",
        distribution_keys=rules.build_industrial_distribution_keys.output,
        config="config/config.yaml",
    output:
        "results/spatial/industrial_energy_demand.csv"
    log:
        "logs/spatial/disaggregate_industrial_energy_demand.log"
    shell:
        (
            'python workflow/scripts/disaggregate_industrial_data.py '
            '--input "{input.demand}" '
            '--keys "{input.distribution_keys}" '
            '--value-column demand '
            '--config "{input.config}" '
            '--output "{output}" '
            '> "{log}" 2>&1'
        )


rule disaggregate_route_production:
    input:
        production="results/demand/route_production.csv",
        distribution_keys=rules.build_industrial_distribution_keys.output,
        config="config/config.yaml",
    output:
        "results/spatial/route_production.csv"
    log:
        "logs/spatial/disaggregate_route_production.log"
    shell:
        (
            'python workflow/scripts/disaggregate_industrial_data.py '
            '--input "{input.production}" '
            '--keys "{input.distribution_keys}" '
            '--value-column route_production '
            '--config "{input.config}" '
            '--output "{output}" '
            '> "{log}" 2>&1'
        )


rule spatial_all:
    input:
        rules.disaggregate_industrial_energy_demand.output,
        rules.disaggregate_route_production.output,
    output:
        touch("results/spatial/.spatial_complete")
