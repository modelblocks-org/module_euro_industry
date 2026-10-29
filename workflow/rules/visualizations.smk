import yaml

# Read visualization settings once when Snakemake parses the workflow.
with open("config/visualization.yaml", "r", encoding="utf-8") as f:
    visualization_cfg = yaml.safe_load(f).get("visualization", {})


plots_output_dir = visualization_cfg.get(
    "output_dir",
    "results/plots",
)

spatial_maps_cfg = visualization_cfg.get(
    "spatial_maps",
    {},
)

maps_output_dir = spatial_maps_cfg.get(
    "output_dir",
    "results/maps",
)


rule plot_results:
    input:
        projected_production="results/projections/production.parquet",
        route_production="results/demand/route_production.parquet",
        energy_demand="results/demand/industrial_energy_demand.parquet",
        visualization_config="config/visualization.yaml",
    output:
        touch(f"{plots_output_dir}/.plots_complete"),
    log:
        "logs/plots/plot_results.log",
    conda:
        "../envs/module.yaml"
    script:
        "../scripts/plot_results.py"


rule plot_spatial_maps:
    input:
        regions=lambda wc: config["spatial_disaggregation"]["regions_file"],
        route_production="results/spatial/route_production.parquet",
        energy_demand="results/spatial/industrial_energy_demand.parquet",
        visualization_config="config/visualization.yaml",
        model_config="config/config.yaml",
    output:
        touch(f"{maps_output_dir}/.maps_complete"),
    log:
        "logs/plots/plot_spatial_maps.log",
    conda:
        "../envs/module.yaml"
    params:
        output_dir=maps_output_dir,
    script:
        "../scripts/plot_spatial_maps.py"


rule plots_all:
    input:
        rules.plot_results.output,
        rules.plot_spatial_maps.output,
    conda:
        "../envs/module.yaml"
