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
        touch("resources/automatic/.downloads_complete")


rule download_eurostat:
    message:
        "Download stable Eurostat energy balances."
    output:
        "resources/automatic/eurostat.zip"
    params:
        url=internal["resources"]["automatic"]["eurostat"]
    log:
        "logs/automatic/download_eurostat.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_jrc_idees:
    message:
        "Download the JRC-IDEES dataset."
    output:
        "resources/automatic/jrc_idees.zip"
    params:
        url=internal["resources"]["automatic"]["jrc_idees"]
    log:
        "logs/automatic/download_jrc_idees.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_hotmaps:
    message:
        "Download the Hotmaps energy-intensive industry dataset."
    output:
        "resources/automatic/hotmaps.csv"
    params:
        url=internal["resources"]["automatic"]["hotmaps"]
    log:
        "logs/automatic/download_hotmaps.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_ammonia_usgs:
    message:
        "Download the U.S. Geological Survey ammonia dataset."
    output:
        "resources/automatic/ammonia/usgs.xlsx"
    params:
        url=internal["resources"]["automatic"]["ammonia"]["usgs"]
    log:
        "logs/automatic/download_ammonia_usgs.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_ammonia_plants:
    message:
        "Download ammonia plants collected by PyPSA-Eur."
    output:
        "resources/automatic/ammonia/plants.csv"
    params:
        url=internal["resources"]["automatic"]["ammonia"]["plants"]
    log:
        "logs/automatic/download_ammonia_plants.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_GEM_SPT:
    message:
        "Download the Global Energy Monitor Steel Plant Tracker."
    output:
        "resources/automatic/GEM_SPT.xlsx"
    params:
        url=internal["resources"]["automatic"]["GEM_SPT"]
    log:
        "logs/automatic/download_GEM_SPT.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_cement_non_eu:
    message:
        "Download non-EU cement plants collected by PyPSA-Eur."
    output:
        "resources/automatic/cement_non_eu.csv"
    params:
        url=internal["resources"]["automatic"]["non_eu"]["cement"]
    log:
        "logs/automatic/download_cement_non_eu.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_refineries_non_eu:
    message:
        "Download non-EU refineries collected by PyPSA-Eur."
    output:
        "resources/automatic/non_eu/refineries.csv"
    params:
        url=internal["resources"]["automatic"]["non_eu"]["refineries"]
    log:
        "logs/automatic/download_refineries_non_eu.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule download_CHE_industry:
    message:
        "Download Swiss industrial production by subsector."
    output:
        "resources/automatic/CHE_industry.csv"
    params:
        url=internal["resources"]["automatic"]["CHE_industry"]
    log:
        "logs/automatic/download_CHE_industry.log"
    shell:
        'python workflow/scripts/download.py --url "{params.url}" --output "{output}" > "{log}" 2>&1'


rule unzip_eurostat:
    message:
        "Extract Eurostat energy balances."
    input:
        "resources/automatic/eurostat.zip"
    output:
        directory("resources/automatic/eurostat")
    log:
        "logs/automatic/unzip_eurostat.log"
    shell:
        'python workflow/scripts/unzip.py --input "{input}" --output "{output}" > "{log}" 2>&1'


rule unzip_jrc_idees:
    message:
        "Extract JRC-IDEES."
    input:
        "resources/automatic/jrc_idees.zip"
    output:
        directory("resources/automatic/jrc_idees")
    log:
        "logs/automatic/unzip_jrc_idees.log"
    shell:
        'python workflow/scripts/unzip.py --input "{input}" --output "{output}" > "{log}" 2>&1'
