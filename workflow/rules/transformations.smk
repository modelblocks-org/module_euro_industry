"""Future industrial route and process transformation layer."""

technologies_file = config["technologies_file"]
scenario_file = config["scenario_file"]


rule transform_industrial_demand:
    input:
        projected_production="results/projections/production.csv",
        historical_production="results/historical/production.csv",
        historical_energy="results/historical/energy_demand.csv",
        technologies=technologies_file,
        scenario=scenario_file,
    output:
        demand="results/demand/industrial_energy_demand.csv",
        route_production="results/demand/route_production.csv",
    log:
        "logs/demand/transform_industrial_demand.log"
    shell:
        'python workflow/scripts/transform_industrial_demand.py '
        '--projected-production "{input.projected_production}" '
        '--historical-production "{input.historical_production}" '
        '--historical-energy "{input.historical_energy}" '
        '--config "config/config.yaml" '
        '--technologies "{input.technologies}" '
        '--scenario "{input.scenario}" '
        '--output-demand "{output.demand}" '
        '--output-route-production "{output.route_production}" '
        '> "{log}" 2>&1'


rule demand_all:
    input:
        rules.transform_industrial_demand.output
    output:
        touch("results/demand/.demand_complete")
