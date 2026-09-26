scenario_file = config["scenario_file"]


rule project_production:
    input:
        reference_production="results/historical/production_aggregated.csv",
        scenario=scenario_file,
    output:
        "results/projections/production.csv"
    log:
        "logs/projections/project_production.log"
    shell:
        (
            'python workflow/scripts/project_production.py '
            '--reference-production "{input.reference_production}" '
            '--config "config/config.yaml" '
            '--scenario "{input.scenario}" '
            '--output "{output}" '
            '> "{log}" 2>&1'
        )


rule projections_all:
    input:
        rules.project_production.output
    output:
        touch("results/projections/.projections_complete")