"""Prepare the historical/current industrial calibration data."""


rule prepare_all:
    input:
        "results/historical/production.csv",
        "results/historical/production_aggregated.csv",
        "results/historical/energy_demand.csv",
    output:
        touch("results/historical/.prepare_complete")


rule prepare_ammonia_production:
    message:
        "Prepare historical ammonia production from USGS."
    input:
        usgs="resources/automatic/ammonia/usgs.xlsx"
    output:
        "resources/automatic/prepare/ammonia_production.csv"
    log:
        "logs/prepare/prepare_ammonia_production.log"
    shell:
        'python workflow/scripts/prepare_ammonia_production.py '
        '--input "{input.usgs}" '
        '--output "{output}" '
        '> "{log}" 2>&1'


rule prepare_coke_transformation:
    message:
        "Prepare historical coke-oven transformation output from Eurostat."
    input:
        eurostat_dir="resources/automatic/eurostat"
    output:
        "resources/automatic/prepare/coke_transformation.csv"
    params:
        countries=" ".join(config["countries"])
    log:
        "logs/prepare/prepare_coke_transformation.log"
    shell:
        'python workflow/scripts/prepare_coke_transformation.py '
        '--eurostat-dir "{input.eurostat_dir}" '
        '--countries {params.countries} '
        '--output "{output}" '
        '> "{log}" 2>&1'


rule prepare_current_production:
    message:
        "Prepare route-preserving historical industrial production."
    input:
        jrc_dir="resources/automatic/jrc_idees",
        eurostat_dir="resources/automatic/eurostat",
        ch_industrial_production="resources/automatic/CHE_industry.csv",
        ammonia_production=rules.prepare_ammonia_production.output,
    output:
        production="results/historical/production.csv",
        aggregated="results/historical/production_aggregated.csv",
    log:
        "logs/prepare/prepare_current_production.log"
    shell:
        'python workflow/scripts/prepare_current_production.py '
        '--config "config/config.yaml" '
        '--jrc-dir "{input.jrc_dir}" '
        '--eurostat-dir "{input.eurostat_dir}" '
        '--ch-industrial-production "{input.ch_industrial_production}" '
        '--ammonia-production "{input.ammonia_production}" '
        '--output "{output.production}" '
        '--aggregated-output "{output.aggregated}" '
        '> "{log}" 2>&1'


rule prepare_current_energy_demand:
    message:
        "Prepare route/activity-preserving historical industrial energy demand."
    input:
        jrc_dir="resources/automatic/jrc_idees",
        production=rules.prepare_current_production.output.production,
        coke=rules.prepare_coke_transformation.output,
    output:
        "results/historical/energy_demand.csv"
    log:
        "logs/prepare/prepare_current_energy_demand.log"
    shell:
        'python workflow/scripts/prepare_current_energy_demand.py '
        '--config "config/config.yaml" '
        '--jrc-dir "{input.jrc_dir}" '
        '--production "{input.production}" '
        '--coke "{input.coke}" '
        '--output "{output}" '
        '> "{log}" 2>&1'