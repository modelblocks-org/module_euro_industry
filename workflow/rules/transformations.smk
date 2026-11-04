"""Future industrial route and process transformation layer."""


rule transform_industrial_demand:
    input:
        projected_production="<projected_production>",
        historical_production="<historical_production>",
        historical_energy="<historical_energy_demand>",
        scenario="<scenario>",
    output:
        demand="<national_industrial_energy_demand>",
        route_production="<national_route_production>",
    log:
        "<logs>/{shapes}/{scenario}/demand/transform_industrial_demand.log",
    conda:
        "../envs/module.yaml"
    params:
        processes=config["technologies"]["processes"],
        production_routes=config["technologies"]["production_routes"],
        reference_year=config["historical_calibration"]["reference_year"],
    script:
        "../scripts/transform_industrial_demand.py"


rule demand_all:
    input:
        rules.transform_industrial_demand.output,
    output:
        touch("<results>/{shapes}/{scenario}/demand/.demand_complete"),
    conda:
        "../envs/module.yaml"
