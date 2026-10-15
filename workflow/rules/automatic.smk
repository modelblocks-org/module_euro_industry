"""Rules for automatically downloaded source datasets."""


rule download_all:
    """Download and extract all external datasets used by the original workflow."""
    input:
        "resources/automatic/eurostat.zip",
        "resources/automatic/jrc_idees.zip",
        "resources/automatic/hotmaps.csv",
        "resources/automatic/ammonia/usgs.xlsx",
        "resources/automatic/ammonia/plants.csv",
        "resources/automatic/GEM_SPT.xlsx",
        # "resources/automatic/cement_non_eu.csv", File cannot be found
        "resources/automatic/non_eu/refineries.csv",
        "resources/automatic/CHE_industry.csv",
        "resources/automatic/eurostat",
        "resources/automatic/jrc_idees",
    output:
        touch("resources/automatic/.downloads_complete"),
    conda:
        "../envs/module.yaml"


rule download_eurostat:
    output:
        "resources/automatic/eurostat.zip",
    log:
        "logs/automatic/download_eurostat.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["eurostat"],
    message:
        "Download stable Eurostat energy balances."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_jrc_idees:
    output:
        "resources/automatic/jrc_idees.zip",
    log:
        "logs/automatic/download_jrc_idees.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["jrc_idees"],
    message:
        "Download the JRC-IDEES dataset."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_hotmaps:
    output:
        "resources/automatic/hotmaps.csv",
    log:
        "logs/automatic/download_hotmaps.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["hotmaps"],
    message:
        "Download the Hotmaps energy-intensive industry dataset."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_ammonia_usgs:
    output:
        "resources/automatic/ammonia/usgs.xlsx",
    log:
        "logs/automatic/download_ammonia_usgs.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["ammonia"]["usgs"],
    message:
        "Download the U.S. Geological Survey ammonia dataset."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_ammonia_plants:
    output:
        "resources/automatic/ammonia/plants.csv",
    log:
        "logs/automatic/download_ammonia_plants.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["ammonia"]["plants"],
    message:
        "Download ammonia plants collected by PyPSA-Eur."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_GEM_SPT:
    output:
        "resources/automatic/GEM_SPT.xlsx",
    log:
        "logs/automatic/download_GEM_SPT.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["GEM_SPT"],
    message:
        "Download the Global Energy Monitor Steel Plant Tracker."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_cement_non_eu:
    output:
        "resources/automatic/cement_non_eu.csv",
    log:
        "logs/automatic/download_cement_non_eu.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["non_eu"]["cement"],
    message:
        "Download non-EU cement plants collected by PyPSA-Eur."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_refineries_non_eu:
    output:
        "resources/automatic/non_eu/refineries.csv",
    log:
        "logs/automatic/download_refineries_non_eu.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["non_eu"]["refineries"],
    message:
        "Download non-EU refineries collected by PyPSA-Eur."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_CHE_industry:
    output:
        "resources/automatic/CHE_industry.csv",
    log:
        "logs/automatic/download_CHE_industry.log",
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["CHE_industry"],
    message:
        "Download Swiss industrial production by subsector."
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule unzip_eurostat:
    input:
        "resources/automatic/eurostat.zip",
    output:
        directory("resources/automatic/eurostat"),
    log:
        "logs/automatic/unzip_eurostat.log",
    conda:
        "../envs/module.yaml"
    message:
        "Extract Eurostat energy balances."
    shell:
        'python workflow/scripts/unzip.py --input "{input}" --output "{output}" > "{log}" 2>&1'


rule unzip_jrc_idees:
    input:
        "resources/automatic/jrc_idees.zip",
    output:
        directory("resources/automatic/jrc_idees"),
    log:
        "logs/automatic/unzip_jrc_idees.log",
    conda:
        "../envs/module.yaml"
    message:
        "Extract JRC-IDEES."
    shell:
        'python workflow/scripts/unzip.py --input "{input}" --output "{output}" > "{log}" 2>&1'
