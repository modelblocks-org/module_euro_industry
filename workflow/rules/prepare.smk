"""Rules in this file focus on parsing and cleaning data."""


rule prepare_population:
    input:
        raster=rules.unzip_GHSL.output[0],
        like_vector="resources/user/{shape}/shapes.parquet",
    output:
        path="resources/automatic/shapes/{shape}/population.tif",
    log:
        "logs/{shape}/prepare_population.log",
    message:
        "{wildcards.shape}: preparing population raster."
    wrapper:
        "v7.9.0/geo/rasterio/clip"


rule prepare_shapes:
    input:
        shapes="resources/user/{shape}/shapes.parquet",
        population=rules.prepare_population.output.path,
    output:
        shapes=temp("resources/automatic/shapes/{shape}/shapes.parquet"),
    log:
        "logs/{shape}/prepare_shapes.log",
    conda:
        "../envs/industry.yaml"
    message:
        "{wildcards.shape}: preparing polygons for European industry disaggregation."
    script:
        "../scripts/prepare_shapes.py"


rule prepare_ammonia_production:
    input:
        usgs=rules.download_ammonia_usgs.output.file,
    output:
        production="resources/automatic/ammonia/production.csv",
    log:
        "logs/prepare/prepare_ammonia_production.log",
    conda:
        "../envs/industry.yaml"
    message:
        "Preparing Global ammonia production statistics."
    script:
        "../scripts/prepare_ammonia_production.py"


rule prepare_coke_transformation:
    input:
        eurostat_dir="resources/automatic/eurostat",
    output:
        coke="resources/automatic/coke/transformation.csv",
    log:
        "logs/prepare/prepare_coke_transformation.log",
    conda:
        "../envs/industry.yaml"
    message:
        "Preparing coke transformation data."
    script:
        "../scripts/prepare_coke_transformation.py"


rule prepare_current_europe_production:
    input:
        ch_industrial_production=rules.download_CHE_industry.output.file,
        ammonia_production=rules.prepare_ammonia_production.output.production,
        jrc_dir="resources/automatic/jrc_idees/",
        eurostat_dir="resources/automatic/eurostat/",
    output:
        production="resources/automatic/europe/current_production.csv",
    log:
        "logs/prepare/prepare_current_europe_production.log",
    conda:
        "../envs/industry.yaml"
    params:
        industry=config["industry"],
    message:
        "Preparing current European production."
    script:
        "../scripts/prepare_current_europe_production.py"


rule prepare_future_europe_production:
    input:
        current=rules.prepare_current_europe_production.output.production,
    output:
        production="resources/automatic/europe/{year}/production.csv",
    log:
        "logs/{year}/prepare_future_europe_production.log",
    conda:
        "../envs/industry.yaml"
    params:
        industry=config["industry"],
    message:
        "{wildcards.year}: preparing future European production."
    script:
        "../scripts/prepare_future_europe_production.py"


rule prepare_current_europe_energy_demand:
    input:
        transformation_output_coke=rules.prepare_coke_transformation.output.coke,
        jrc="resources/automatic/jrc_idees",
        industrial_production_per_country=rules.prepare_current_europe_production.output.production,
    output:
        energy_demand="resources/automatic/europe/current_energy_demand.csv",
    log:
        "logs/prepare/prepare_current_europe_energy_demand.log",
    conda:
        "../envs/industry.yaml"
    params:
        industry=config["industry"],
        ammonia=config["ammonia"],
    message:
        "Preparing current energy demand for European nations."
    script:
        "../scripts/prepare_current_europe_energy_demand.py"


# TODO: rename to rates mentioning it's 'best in class rates' or something like that?
rule prepare_sector_ratios:
    input:
        ammonia_production=rules.prepare_ammonia_production.output.production,
        idees="resources/automatic/jrc_idees",
    output:
        industry_sector_ratios="resources/automatic/europe/sector_ratios_eu27.csv",
    log:
        "logs/prepare/prepare_sector_ratios.log",
    conda:
        "../envs/industry.yaml"
    params:
        industry=config["industry"],
        ammonia=config["ammonia"],
    message:
        "Preparing average energy demand rates per industrial subsector."
    script:
        "../scripts/prepare_sector_ratios.py"


rule prepare_future_europe_sector_rates:
    input:
        sector_rates=rules.prepare_sector_ratios.output.industry_sector_ratios,
        current_european_demand=rules.prepare_current_europe_energy_demand.output.energy_demand,
        future_european_production=rules.prepare_future_europe_production.output.production,
    output:
        sector_rates="resources/automatic/europe/{year}/sector_rates.csv",
    log:
        "logs/{year}/prepare_future_europe_sector_rates.log",
    conda:
        "../envs/industry.yaml"
    params:
        industry=config["industry"],
    message:
        "Preparing future rates by interpolating between current and future best-in-class consumption."
    script:
        "../scripts/prepare_future_europe_sector_rates.py"
