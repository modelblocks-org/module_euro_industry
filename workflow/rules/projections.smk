scenario_file = config["scenario_file"]


rule project_production:
    input:
        reference_production="results/historical/production_aggregated.parquet",
        scenario=scenario_file,
    output:
        "results/projections/production.parquet",
    log:
        "logs/projections/project_production.log",
    conda:
        "../envs/module.yaml"
    params:
        config_path="config/config.yaml",
    script:
        "../scripts/project_production.py"


rule projections_all:
    input:
        rules.project_production.output,
    output:
        touch("results/projections/.projections_complete"),
    conda:
        "../envs/module.yaml"
