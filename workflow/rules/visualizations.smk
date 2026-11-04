rule plot_results:
    input:
        projected_production="<projected_production>",
        route_production="<national_route_production>",
        energy_demand="<national_industrial_energy_demand>",
    output:
        touch("<plots>"),
    log:
        "<logs>/{shapes}/plots/plot_results.log",
    conda:
        "../envs/module.yaml"
    params:
        include_plots=config["visualization"]["include_plots"],
        energy_layer=config["visualization"]["energy_layer"],
    script:
        "../scripts/plot_results.py"


rule plot_spatial_maps:
    input:
        regions=rules.prepare_shapes.output.shapes,
        route_production="<route_production>",
        energy_demand="<industrial_energy_demand>",
    output:
        touch("<maps>"),
    log:
        "<logs>/{shapes}/plots/plot_spatial_maps.log",
    conda:
        "../envs/module.yaml"
    params:
        include_plots=config["visualization"]["include_plots"],
        energy_layer=config["visualization"]["energy_layer"],
    script:
        "../scripts/plot_spatial_maps.py"


rule plots_all:
    input:
        rules.plot_results.output,
        rules.plot_spatial_maps.output,
    conda:
        "../envs/module.yaml"
