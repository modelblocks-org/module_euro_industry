"""Rules to used to download automatic resource files."""


rule download_eurostat:
    output:
        file=temp("resources/automatic/eurostat.zip"),
    log:
        "logs/automatic/download_eurostat.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["eurostat"],
    message:
        "Download stable Eurostat energy balances."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_jrc_idees:
    output:
        file=temp("resources/automatic/jrc_idees.zip"),
    log:
        "logs/automatic/download_jrc_idees.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["jrc_idees"],
    message:
        "Download the JRC IDEES dataset."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_hotmaps:
    output:
        file="resources/automatic/hotmaps.csv",
    log:
        "logs/automatic/download_hotmaps.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["hotmaps"],
    message:
        "Download the Hotmaps energy intensive industry dataset."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_ammonia_usgs:
    output:
        file=temp("resources/automatic/ammonia/usgs.xlsx"),
    log:
        "logs/automatic/download_ammonia_usgs.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["ammonia"]["usgs"],
    message:
        "Download the U.S. geological survey on ammonia supply."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_ammonia_plants:
    output:
        file="resources/automatic/ammonia/plants.csv",
    log:
        "logs/automatic/download_ammonia_plants.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["ammonia"]["plants"],
    message:
        "Download ammonia plants as collected by PyPSA-Eur."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_GEM_SPT:
    output:
        file="resources/automatic/GEM_SPT.xlsx",
    log:
        "logs/automatic/download_GEM_SPT.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["GEM_SPT"],
    message:
        "Download the Global Energy Monitor - Steel Plant Tracker."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_cement_non_eu:
    output:
        file="resources/automatic/cement_non_eu.csv",
    log:
        "logs/automatic/download_cement_non_eu.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["non_eu"]["cement"],
    message:
        "Download cement plants as collected by PyPSA-Eur."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_refineries_non_eu:
    output:
        file="resources/automatic/non_eu/refineries.csv",
    log:
        "logs/automatic/download_refineries_non_eu.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["non_eu"]["refineries"],
    message:
        "Download refineries as collected by PyPSA-Eur."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_CHE_industry:
    output:
        file="resources/automatic/CHE_industry.csv",
    log:
        "logs/automatic/download_CHE_industry.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["CHE_industry"],
    message:
        "Download CHE industrial production per subsector."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule download_GHSL_population:
    output:
        file=temp("resources/automatic/GHSL.zip"),
    log:
        "logs/automatic/download_CHE_industry.log",
    conda:
        "../envs/shell.yaml"
    params:
        url=get_ghsl_url(
            internal["population"]["epoch"], internal["population"]["resolution"]
        ),
    message:
        "Download the Global Human Settlement Layer population raster."
    shell:
        'curl -sSLo {output.file} "{params.url}"'


rule unzip_directory:
    input:
        zip_file="resources/automatic/{directory}.zip",
    output:
        directory("resources/automatic/{directory}/"),
    log:
        "logs/automatic/unzip_directory_{directory}.log",
    wildcard_constraints:
        directory="|".join({"eurostat", "jrc_idees"}),
    conda:
        "../envs/industry.yaml"
    message:
        "Unzipping {wildcards.directory}."
    script:
        "../scripts/unzip.py"


# TODO: standardised epoch and resolution, or user configured?
rule unzip_GHSL:
    input:
        zip_file="resources/automatic/GHSL.zip",
    output:
        "resources/automatic/GHSL.tif",
    log:
        "logs/automatic/unzip_GHSL.log",
    conda:
        "../envs/industry.yaml"
    params:
        file=f"GHS_POP_E{internal['population']['epoch']}_GLOBE_R2023A_54009_{internal['population']['resolution']}_V1_0.tif",
    message:
        "Unzipping {params.file}."
    script:
        "../scripts/unzip.py"
