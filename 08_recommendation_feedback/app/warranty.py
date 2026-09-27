DIRECTORY = {  # region -> contacts, versioned separately from code
    "TH": [{"manufacturer": "AMD", "phone": "+66-2-000-0001"}, {"manufacturer": "NVIDIA", "phone": "+66-2-000-0002"}],
    "US": [{"manufacturer": "AMD", "phone": "+1-800-000-0001"}, {"manufacturer": "NVIDIA", "phone": "+1-800-000-0002"}],
}
def contacts_for(locale: str, directory_version: str):
    region = "TH" if locale.endswith("TH") else "US"
    return [{"manufacturer": c["manufacturer"], "region": region, "phone": c["phone"], "effective_date": directory_version + "-01"}
            for c in DIRECTORY.get(region, DIRECTORY["US"])]
