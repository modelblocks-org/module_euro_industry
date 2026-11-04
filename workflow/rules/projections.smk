rule project_production:
    input:
        reference_production="<historical_production_aggregated>",
        scenario="<scenario>",
    output:
        production="<projected_production>",
    log:
        "<logs>/{shapes}/{scenario}/projections/project_production.log",
    conda:
        "../envs/module.yaml"
    params:
        reference_year=config["historical_calibration"]["reference_year"],
    script:
        "../scripts/project_production.py"


rule projections_all:
    input:
        rules.project_production.output,
    output:
        touch("<results>/{shapes}/{scenario}/projections/.projections_complete"),
    conda:
        "../envs/module.yaml"
