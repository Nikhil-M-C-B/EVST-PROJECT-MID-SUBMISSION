import re, warnings, sys, traceback
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from scipy import stats as scipy_stats

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
RAW  = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIG  = ROOT / "outputs" / "figures"
TABS = ROOT / "outputs" / "tables"
STAT = ROOT / "outputs" / "statistics"
for d in [PROC, FIG, TABS, STAT]:
    d.mkdir(parents=True, exist_ok=True)

MID_EVAL_FIGURES = {
    "fig1_cmur_trend.png", "fig2_cmur_ranking.png", "fig3_cmur_trajectories.png",
    "fig4_dmc_trends.png", "fig5_cmur_vs_dmc.png", "fig6_cmur_vs_de.png",
    "fig7_gdp_vs_dmc.png", "fig8_decoupling_counts.png", "fig9_dmc_per_capita.png",
    "fig11_oecd_vs_unep.png", "fig12_case_studies.png", "fig17_dmc_change_bar.png",
    "fig18_quadrant_classification.png", "fig19_tapio_classification.png",
    "fig23_cmur_vs_dmi.png",
}
MID_EVAL_TABLES = {
    "case_studies_detail.csv", "dataset_inventory.csv", "decoupling_table.csv",
    "final_results_table.csv", "final_results_table.xlsx",
    "quadrant_classification.csv", "recycling_performance.csv",
    "sensitivity_analysis.csv", "tapio_classification.csv",
}
MID_EVAL_STATISTICS = {
    "cmur_threshold_sensitivity.csv", "correlation_analysis.csv",
    "country_level_correlations.csv", "descriptive_statistics.csv",
    "oecd_robustness.csv", "outlier_analysis.csv", "unsdg_validation.csv",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 11, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "figure.dpi": 150,
})
PAL = {"blue": "#2196F3", "green": "#4CAF50", "red": "#F44336",
       "orange": "#FF9800", "purple": "#9C27B0", "grey": "#9E9E9E",
       "dark": "#212121", "teal": "#009688"}
CPAL = list(PAL.values())

# ── Constants ─────────────────────────────────────────────────────────────────
MIN_POP       = 1_000_000   # Fix #1: strict population filter
START_YEAR    = 2010        # Fix #8: strict common window
END_YEAR      = 2022        # Fix #8

EU27_ISO3 = [
    "AUT","BEL","BGR","CYP","CZE","DEU","DNK","EST","GRC","ESP","FIN","FRA",
    "HRV","HUN","IRL","ITA","LTU","LUX","LVA","MLT","NLD","POL","PRT","ROU",
    "SWE","SVN","SVK",
]
EU_NAMES = {
    "AUT":"Austria","BEL":"Belgium","BGR":"Bulgaria","CYP":"Cyprus",
    "CZE":"Czechia","DEU":"Germany","DNK":"Denmark","EST":"Estonia",
    "GRC":"Greece","ESP":"Spain","FIN":"Finland","FRA":"France",
    "HRV":"Croatia","HUN":"Hungary","IRL":"Ireland","ITA":"Italy",
    "LTU":"Lithuania","LUX":"Luxembourg","LVA":"Latvia","MLT":"Malta",
    "NLD":"Netherlands","POL":"Poland","PRT":"Portugal","ROU":"Romania",
    "SWE":"Sweden","SVN":"Slovenia","SVK":"Slovakia",
}
EUROSTAT_ISO2_ISO3 = {
    "AT":"AUT","BE":"BEL","BG":"BGR","CY":"CYP","CZ":"CZE",
    "DE":"DEU","DK":"DNK","EE":"EST","EL":"GRC","ES":"ESP",
    "EU27_2020":"EU27","FI":"FIN","FR":"FRA","HR":"HRV","HU":"HUN",
    "IE":"IRL","IT":"ITA","LT":"LTU","LU":"LUX","LV":"LVA","MT":"MLT",
    "NL":"NLD","PL":"POL","PT":"PRT","RO":"ROU","SE":"SWE",
    "SI":"SVN","SK":"SVK",
}
UNEP_EXCLUDE = {
    "World","Africa","Asia + Pacific","Europe",
    "Latin America + Caribbean","North America","West Asia",
    "USSR","Sudan (Former)","Ethiopia (Former)",
    "Czechoslovakia","Yugoslavia","Netherlands Antilles",
}
UNEP_ISO3 = {
    "Afghanistan":"AFG","Albania":"ALB","Algeria":"DZA","Angola":"AGO",
    "Argentina":"ARG","Armenia":"ARM","Australia":"AUS","Austria":"AUT",
    "Azerbaijan":"AZE","Bahamas":"BHS","Bahrain":"BHR","Bangladesh":"BGD",
    "Belarus":"BLR","Belgium":"BEL","Belize":"BLZ","Benin":"BEN",
    "Bhutan":"BTN","Bolivia (Plurinational State of)":"BOL",
    "Bosnia and Herzegovina":"BIH","Botswana":"BWA","Brazil":"BRA",
    "Brunei Darussalam":"BRN","Bulgaria":"BGR","Burkina Faso":"BFA",
    "Burundi":"BDI","Cambodia":"KHM","Cameroon":"CMR","Canada":"CAN",
    "Central African Republic":"CAF","Chad":"TCD","Chile":"CHL",
    "China, Hong Kong SAR":"HKG","China, Macao SAR":"MAC",
    "China, mainland":"CHN","China, Taiwan Province of":"TWN",
    "Colombia":"COL","Congo":"COG","Costa Rica":"CRI","Croatia":"HRV",
    "Cuba":"CUB","Cyprus":"CYP","Czech Republic":"CZE","Czechia":"CZE",
    "Cote d'Ivoire":"CIV","Côte d'Ivoire":"CIV",
    "Democratic People's Republic of Korea":"PRK",
    "Democratic Republic of the Congo":"COD","Denmark":"DNK",
    "Dominican Republic":"DOM","Ecuador":"ECU","Egypt":"EGY",
    "El Salvador":"SLV","Eritrea":"ERI","Estonia":"EST","Eswatini":"SWZ",
    "Ethiopia":"ETH","Finland":"FIN","France":"FRA",
    "French Polynesia":"PYF","Gabon":"GAB","Gambia":"GMB","Georgia":"GEO",
    "Germany":"DEU","Ghana":"GHA","Greece":"GRC","Guatemala":"GTM",
    "Guinea":"GIN","Guinea-Bissau":"GNB","Haiti":"HTI","Honduras":"HND",
    "Hungary":"HUN","Iceland":"ISL","India":"IND","Indonesia":"IDN",
    "Iran (Islamic Republic of)":"IRN","Iraq":"IRQ","Ireland":"IRL",
    "Israel":"ISR","Italy":"ITA","Jamaica":"JAM","Japan":"JPN",
    "Jordan":"JOR","Kazakhstan":"KAZ","Kenya":"KEN","Kosovo":"XKX",
    "Kuwait":"KWT","Kyrgyzstan":"KGZ",
    "Lao People's Democratic Republic":"LAO","Latvia":"LVA","Lebanon":"LBN",
    "Lesotho":"LSO","Liberia":"LBR","Libyan Arab Jamahiriya":"LBY",
    "Lithuania":"LTU","Luxembourg":"LUX","Madagascar":"MDG","Malawi":"MWI",
    "Malaysia":"MYS","Mali":"MLI","Malta":"MLT","Mauritania":"MRT",
    "Mauritius":"MUS","Mexico":"MEX","Republic of Moldova":"MDA",
    "Mongolia":"MNG","Morocco":"MAR","Mozambique":"MOZ","Myanmar":"MMR",
    "Namibia":"NAM","Nepal":"NPL","Netherlands":"NLD",
    "Netherlands (Kingdom of the)":"NLD","New Zealand":"NZL",
    "Nicaragua":"NIC","Niger":"NER","Nigeria":"NGA",
    "North Macedonia":"MKD","Norway":"NOR","Oman":"OMN","Pakistan":"PAK",
    "Panama":"PAN","Papua New Guinea":"PNG","Paraguay":"PRY","Peru":"PER",
    "Philippines":"PHL","Poland":"POL","Portugal":"PRT","Qatar":"QAT",
    "Republic of Korea":"KOR","Romania":"ROU","Russian Federation":"RUS",
    "Rwanda":"RWA","Saudi Arabia":"SAU","Senegal":"SEN","Serbia":"SRB",
    "Sierra Leone":"SLE","Singapore":"SGP","Slovakia":"SVK",
    "Slovenia":"SVN","Somalia":"SOM","South Africa":"ZAF","Spain":"ESP",
    "Sri Lanka":"LKA","Sudan":"SDN","Sweden":"SWE","Switzerland":"CHE",
    "Syrian Arab Republic":"SYR","Tajikistan":"TJK","Tanzania":"TZA",
    "Thailand":"THA","Timor-Leste":"TLS","Togo":"TGO",
    "Trinidad and Tobago":"TTO","Tunisia":"TUN","Turkiye":"TUR",
    "Turkey":"TUR","Turkmenistan":"TKM","Uganda":"UGA","Ukraine":"UKR",
    "United Arab Emirates":"ARE","United Kingdom":"GBR",
    "United Republic of Tanzania":"TZA","United States of America":"USA",
    "Uruguay":"URY","Uzbekistan":"UZB",
    "Venezuela (Bolivarian Republic of)":"VEN","Viet Nam":"VNM",
    "West Bank and Gaza Strip":"PSE","Yemen":"YEM","Zambia":"ZMB",
    "Zimbabwe":"ZWE","Micronesia (Federated States of)":"FSM",
    "The former Yugoslav Republic of Macedonia":"MKD",
    "Saint Kitts and Nevis":"KNA","Saint Lucia":"LCA",
    "Saint Vincent and the Grenadines":"VCT","Sao Tome and Principe":"STP",
    "American Samoa":"ASM","Andorra":"AND","Anguilla":"AIA",
    "Antigua and Barbuda":"ATG","Aruba":"ABW","Barbados":"BRB",
    "Comoros":"COM","Djibouti":"DJI","Dominica":"DMA","Equatorial Guinea":"GNQ",
    "Fiji":"FJI","Grenada":"GRD","Guam":"GUM","Guyana":"GUY",
    "Kiribati":"KIR","Libya":"LBY","Maldives":"MDV",
    "Marshall Islands":"MHL","Micronesia":"FSM","Namibia":"NAM",
    "Nauru":"NRU","New Caledonia":"NCL","Palau":"PLW",
    "Puerto Rico":"PRI","Samoa":"WSM","Seychelles":"SYC","Solomon Islands":"SLB",
    "Suriname":"SUR","Tonga":"TON","Tuvalu":"TUV","Vanuatu":"VUT",
    "Virgin Islands (U.S.)":"VIR","Cabo Verde":"CPV","Mozambique":"MOZ",
}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _save(fig, name):
    if name not in MID_EVAL_FIGURES:
        plt.close(fig)
        return
    p = FIG / name
    fig.savefig(p, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"    [Fig] {name}")

def _save_csv(frame, directory, name):
    allowed = MID_EVAL_TABLES if directory == TABS else MID_EVAL_STATISTICS
    if name in allowed:
        frame.to_csv(directory / name, index=False)

def _pct(a, b):
    if pd.isna(a) or pd.isna(b) or a == 0:
        return np.nan
    return (b - a) / abs(a) * 100

def _first_last_strict(grp, col, y1, y2):
    """Return value at y1 and y2 exactly (strict window)."""
    v1 = grp.loc[grp["year"] == y1, col]
    v2 = grp.loc[grp["year"] == y2, col]
    r1 = v1.iloc[0] if len(v1) == 1 and not pd.isna(v1.iloc[0]) else np.nan
    r2 = v2.iloc[0] if len(v2) == 1 and not pd.isna(v2.iloc[0]) else np.nan
    return r1, r2

def _phase(n, title, critical=False):
    print(f"\n{'='*66}")
    print(f"  PHASE {n} — {title}")
    print(f"{'='*66}")

def _fail(msg):
    """Fix #14: stop on critical validation failure."""
    print(f"\n  !! CRITICAL VALIDATION FAILURE: {msg}")
    print("  Pipeline halted. Fix the data issue before re-running.")
    sys.exit(1)

def _warn(msg):
    print(f"  [WARN] {msg}")


# ══════════════════════════════════════════════════════════════════════════════
_phase(1, "DATA CLEANING — ALL 5 SOURCES")
# ══════════════════════════════════════════════════════════════════════════════

# ── UNEP ──────────────────────────────────────────────────────────────────────
print("  Cleaning UNEP...")
unep_raw = pd.read_csv(RAW / "UNEP.csv")
yr_cols  = [c for c in unep_raw.columns if re.fullmatch(r"\d{4}", str(c))]
unep = unep_raw.melt(id_vars=["Country","Flow name","Flow code","Flow unit"],
                     value_vars=yr_cols, var_name="year", value_name="value")
unep.columns = ["country","flow_name","flow_code","unit","year","value"]
unep["year"]  = unep["year"].astype(int)
unep["value"] = pd.to_numeric(unep["value"], errors="coerce")

# Remove declared regional aggregates
n_before = len(unep)
unep = unep[~unep["country"].isin(UNEP_EXCLUDE)]
n_agg_removed = n_before - len(unep)

# Remove DMC <= 0 (Fix #1-related; bad values)
dmc_mask = (unep["flow_code"] == "DMC") & (unep["value"] <= 0) & unep["value"].notna()
n_zero_dmc = dmc_mask.sum()
unep.loc[dmc_mask, "value"] = np.nan
unep = unep.dropna(subset=["value"])

# Assign ISO-3
unep["iso3"] = unep["country"].map(UNEP_ISO3).fillna("UNKNOWN")

# Fix #7: inspect UNKNOWN entities — remove non-countries
unknown_countries = unep[unep["iso3"] == "UNKNOWN"]["country"].unique()
if len(unknown_countries):
    print(f"    UNEP UNKNOWN entities ({len(unknown_countries)}): {sorted(unknown_countries)}")
    # Remove genuine non-countries (territories, etc.) — keep only if they
    # plausibly appear in our EU/global analysis, otherwise exclude
    # These are small territories; none are EU-27 members
    n_before_unk = len(unep)
    unep = unep[unep["iso3"] != "UNKNOWN"]
    print(f"    Removed {n_before_unk - len(unep):,} rows with unresolved ISO-3")
else:
    print("    No UNKNOWN entities in UNEP — OK")

unep.to_csv(PROC / "unep_clean.csv", index=False)
print(f"  [UNEP] {len(unep):,} rows | {unep['country'].nunique()} countries | "
      f"{unep['year'].min()}–{unep['year'].max()}")
print(f"    Aggregates removed: {n_agg_removed:,} | DMC≤0 set NaN: {n_zero_dmc}")

# ── OECD ──────────────────────────────────────────────────────────────────────
print("\n  Cleaning OECD...")
oecd_raw = pd.read_csv(RAW / "OECD.csv", low_memory=False)

# Fix #5: explicitly verify MEASURE and UNIT_MEASURE before using
print(f"    OECD MEASURE values: {sorted(oecd_raw['MEASURE'].unique())}")
print(f"    OECD UNIT_MEASURE values: {sorted(oecd_raw['Unit of measure'].unique())}")
# Expect: MEASURE == 'DMC', UNIT_MEASURE == 'Tonnes per person'
valid_measure = oecd_raw["MEASURE"].isin(["DMC"])
valid_unit    = oecd_raw["Unit of measure"].isin(["Tonnes per person"])
n_before_oecd = len(oecd_raw)
oecd_filtered = oecd_raw[valid_measure & valid_unit].copy()
if len(oecd_filtered) == 0:
    _fail("OECD: no rows match MEASURE=DMC and UNIT=Tonnes per person")
print(f"    Rows before filter: {n_before_oecd:,} → after: {len(oecd_filtered):,}")

oecd = oecd_filtered[["REF_AREA","Reference area","MEASURE",
                       "Unit of measure","TIME_PERIOD","OBS_VALUE"]].copy()
oecd.columns = ["iso3","country_name","measure","unit","year","value"]
oecd["year"]  = pd.to_numeric(oecd["year"],  errors="coerce").astype("Int64")
oecd["value"] = pd.to_numeric(oecd["value"], errors="coerce")
oecd = oecd.dropna(subset=["value","year"])

# Fix #5: verify one obs per country-year
oecd_dup = oecd.groupby(["iso3","year"]).size()
n_oecd_dup = (oecd_dup > 1).sum()
if n_oecd_dup > 0:
    _warn(f"OECD has {n_oecd_dup} duplicate country-year combinations — taking first")
    oecd = oecd.drop_duplicates(subset=["iso3","year"], keep="first")

oecd = oecd.sort_values(["iso3","year"]).reset_index(drop=True)
oecd.to_csv(PROC / "oecd_clean.csv", index=False)
print(f"  [OECD] {len(oecd):,} rows | {oecd['iso3'].nunique()} countries | "
      f"{int(oecd['year'].min())}–{int(oecd['year'].max())}")
print(f"    Measure: DMC t/person | Duplicates removed: {n_oecd_dup}")

# ── Eurostat ──────────────────────────────────────────────────────────────────
print("\n  Cleaning Eurostat...")
eu_raw = pd.read_csv(RAW / "EUROSTAT.csv")

# Fix #6: verify single series and unique country-year
eu_series = eu_raw["STRUCTURE_NAME"].unique()
print(f"    Eurostat series found: {eu_series}")
if len(eu_series) != 1 or "Circular material use rate" not in eu_series[0]:
    _fail(f"Eurostat file contains unexpected series: {eu_series}")

# Fix #6: verify uniqueness
eurostat = eu_raw[["geo","Geopolitical entity (reporting)",
                   "TIME_PERIOD","OBS_VALUE","STRUCTURE_NAME","unit"]].copy()
eurostat.columns = ["iso2","country_name","year","cmur","indicator","unit"]
eurostat["iso3"] = eurostat["iso2"].map(EUROSTAT_ISO2_ISO3)
eurostat["year"] = pd.to_numeric(eurostat["year"], errors="coerce").astype("Int64")
eurostat["cmur"] = pd.to_numeric(eurostat["cmur"], errors="coerce")
eurostat["suspect_flag"] = (eurostat["cmur"] < 0) | (eurostat["cmur"] > 100)

# EL→GRC check
el_check = eurostat[eurostat["iso2"]=="EL"]["iso3"].unique()
if "GRC" not in el_check:
    _fail("EL→GRC mapping failed")
print(f"    EL→GRC mapping: {el_check} ✓")

# Check uniqueness
eu_dup = eurostat.groupby(["iso3","year"]).size()
n_eu_dup = (eu_dup > 1).sum()
if n_eu_dup > 0:
    _warn(f"Eurostat: {n_eu_dup} duplicate country-year combos — keeping first")
    eurostat = eurostat.drop_duplicates(subset=["iso3","year"], keep="first")

n_countries_eu = eurostat[eurostat["iso3"] != "EU27"]["iso3"].nunique()
print(f"    Countries: {n_countries_eu} (27 expected)")
if n_countries_eu != 27:
    _warn(f"Eurostat has {n_countries_eu} individual countries, expected 27")

eurostat.to_csv(PROC / "eurostat_clean.csv", index=False)
print(f"  [EUROSTAT] {len(eurostat):,} rows | {n_countries_eu} EU countries + EU27 aggregate")
print(f"    CMUR range: {eurostat['cmur'].min():.1f}–{eurostat['cmur'].max():.1f}%")
print(f"    Years: {int(eurostat['year'].min())}–{int(eurostat['year'].max())}")

# ── UN SDG ────────────────────────────────────────────────────────────────────
print("\n  Cleaning UN-SDG...")
sdg_raw = pd.read_csv(RAW / "UN-SDG.csv", low_memory=False)
mat_series = ["EN_MAT_DOMCMPC","EN_MAT_DOMCMPG","EN_MAT_DOMCMPT"]
unsdg = sdg_raw[sdg_raw["SeriesCode"].isin(mat_series)].copy()
keep_sdg = {"SeriesCode":"series_code","SeriesDescription":"series_desc",
            "GeoAreaCode":"geo_code","GeoAreaName":"country_name",
            "TimePeriod":"year","Value":"value","Units":"units",
            "Type of product":"material_type"}
unsdg = unsdg[[c for c in keep_sdg if c in unsdg.columns]].rename(columns=keep_sdg)
unsdg["year"]  = pd.to_numeric(unsdg["year"],  errors="coerce").astype("Int64")
unsdg["value"] = pd.to_numeric(unsdg["value"], errors="coerce")

# Fix #2: build ISO-3 mapping for ALL countries, not just EU
# Use the UNEP map extended with common SDG names
SDG_NAME_MAP = {**{v: k for k, v in EU_NAMES.items()}, **UNEP_ISO3}
SDG_NAME_MAP.update({
    "United States of America": "USA",
    "Russian Federation": "RUS",
    "China, mainland": "CHN",
    "Republic of Korea": "KOR",
    "China": "CHN",
    "Iran (Islamic Republic of)": "IRN",
    "Viet Nam": "VNM",
    "Czechia": "CZE",
    "Republic of Moldova": "MDA",
    "Bolivia (Plurinational State of)": "BOL",
    "Venezuela (Bolivarian Republic of)": "VEN",
    "Lao People's Democratic Republic": "LAO",
    "Democratic Republic of the Congo": "COD",
    "United Republic of Tanzania": "TZA",
    "Eswatini": "SWZ",
    "North Macedonia": "MKD",
    "Côte d'Ivoire": "CIV",
    "Cote d'Ivoire": "CIV",
    "Brunei Darussalam": "BRN",
    "Syrian Arab Republic": "SYR",
    "Kyrgyzstan": "KGZ",
    "Tajikistan": "TJK",
    "Turkmenistan": "TKM",
    "Micronesia (Federated States of)": "FSM",
    "Timor-Leste": "TLS",
    "Sao Tome and Principe": "STP",
    "Saint Kitts and Nevis": "KNA",
    "Saint Lucia": "LCA",
    "Saint Vincent and the Grenadines": "VCT",
    "West Bank and Gaza Strip": "PSE",
    "Kosovo": "XKX",
    "Turkiye": "TUR",
    "Turkey": "TUR",
    "Netherlands (Kingdom of the)": "NLD",
    "China, Hong Kong SAR": "HKG",
    "China, Macao SAR": "MAC",
    "China, Taiwan Province of": "TWN",
    "Libyan Arab Jamahiriya": "LBY",
    "Libya": "LBY",
    "Cabo Verde": "CPV",
    "Comoros": "COM",
    "The former Yugoslav Republic of Macedonia": "MKD",
    "Sudan (former)": "SDN",
})
unsdg["iso3"] = unsdg["country_name"].map(SDG_NAME_MAP).fillna("UNKNOWN")
unsdg = unsdg.dropna(subset=["value"]).reset_index(drop=True)
unsdg.to_csv(PROC / "unsdg_clean.csv", index=False)
print(f"  [UN-SDG] {len(unsdg):,} rows | {unsdg['country_name'].nunique()} areas | "
      f"{int(unsdg['year'].min())}–{int(unsdg['year'].max())}")
print(f"    ISO-3 mapped: {(unsdg['iso3']!='UNKNOWN').sum()} | UNKNOWN: {(unsdg['iso3']=='UNKNOWN').sum()}")
for sc in mat_series:
    sub = unsdg[unsdg["series_code"]==sc]
    print(f"    {sc}: {len(sub):,} rows | types: {sorted(sub['material_type'].unique())}")

# ── World Bank ─────────────────────────────────────────────────────────────────
print("\n  Cleaning World Bank...")
def _read_wb(path, vcol):
    raw = pd.read_csv(path, skiprows=4, encoding="utf-8-sig")
    raw = raw.dropna(subset=["Country Name"])
    ycs = [c for c in raw.columns if re.fullmatch(r"\d{4}", str(c))]
    long = raw.melt(id_vars=["Country Name","Country Code"],
                    value_vars=ycs, var_name="year", value_name=vcol)
    long.columns = ["country_name","iso3","year",vcol]
    long["year"] = long["year"].astype(int)
    long[vcol]   = pd.to_numeric(long[vcol], errors="coerce")
    return long

gdp_wb = _read_wb(RAW / "WORLDBANK-GDP.csv",        "gdp_current_usd")
pop_wb = _read_wb(RAW / "WORLDBANK-POPULATION.csv",  "population")
wb     = gdp_wb.merge(pop_wb, on=["country_name","iso3","year"], how="outer")
wb     = wb.dropna(subset=["gdp_current_usd","population"], how="all")
wb     = wb.sort_values(["iso3","year"]).reset_index(drop=True)
wb.to_csv(PROC / "worldbank_clean.csv", index=False)
print(f"  [WB] {len(wb):,} rows | note: GDP in CURRENT USD (supplementary only)")
print(f"  ✓ Phase 1 complete — all 5 sources cleaned")


# ══════════════════════════════════════════════════════════════════════════════
_phase(2, "VALIDATION CHECKS — must pass before analysis")
# ══════════════════════════════════════════════════════════════════════════════

print("\n  [V1] EUROSTAT: single series, 27 EU countries, no duplicates")
eu_only = eurostat[eurostat["iso3"] != "EU27"]
assert eu_only["iso3"].nunique() == 27, "Not 27 EU countries in Eurostat"
assert eu_only.groupby(["iso3","year"]).size().max() == 1, "Duplicate country-year in Eurostat"
print("    PASS: 27 EU countries, no duplicate country-year")

print("  [V2] UNEP: no declared aggregates, no UNKNOWN iso3, no DMC<=0")
for exc in UNEP_EXCLUDE:
    assert exc not in unep["country"].values, f"Aggregate still present: {exc}"
assert (unep["iso3"] == "UNKNOWN").sum() == 0, "UNKNOWN iso3 still in UNEP"
assert ((unep["flow_code"]=="DMC") & (unep["value"]<=0)).sum() == 0, "DMC<=0 in UNEP"
print("    PASS: no aggregates, no UNKNOWN, no DMC<=0")

print("  [V3] OECD: DMC / tonnes-per-person, no duplicates")
assert (oecd["measure"]=="DMC").all(), "Non-DMC rows in OECD"
assert (oecd["unit"]=="Tonnes per person").all(), "Wrong unit in OECD"
assert oecd.groupby(["iso3","year"]).size().max() == 1, "OECD duplicates"
print("    PASS: DMC, t/person, no duplicates")

print("  [V4] GDP-real formula validation")
# Formula: GDP_const2020 = DMC_t × 1000 / (DMC_kg_per_USD)
# Check Germany 2020 ≈ 3.9 trillion USD
sdg_t_alp  = unsdg[(unsdg["series_code"]=="EN_MAT_DOMCMPT") & (unsdg["material_type"]=="ALP")].copy()
sdg_g_alp  = unsdg[(unsdg["series_code"]=="EN_MAT_DOMCMPG") & (unsdg["material_type"]=="ALP")].copy()
sdg_t_alp  = sdg_t_alp.rename(columns={"value":"dmc_t_sdg"})
sdg_g_alp  = sdg_g_alp.rename(columns={"value":"dmc_gdp_sdg"})
gdp_real   = sdg_t_alp[["country_name","iso3","year","dmc_t_sdg"]].merge(
    sdg_g_alp[["country_name","iso3","year","dmc_gdp_sdg"]],
    on=["country_name","iso3","year"], how="inner"
)
gdp_real   = gdp_real[gdp_real["dmc_gdp_sdg"] > 0].copy()
gdp_real["gdp_real_const2020"] = (gdp_real["dmc_t_sdg"] * 1000.0) / gdp_real["dmc_gdp_sdg"]
gdp_real["year"] = gdp_real["year"].astype(int)

deu20 = gdp_real[(gdp_real["iso3"]=="DEU") & (gdp_real["year"]==2020)]
if len(deu20) == 0:
    _warn("Germany 2020 not found in real-GDP series — check UN-SDG mapping")
else:
    v_deu = deu20["gdp_real_const2020"].iloc[0]
    if not (3e12 < v_deu < 5e12):
        _fail(f"Germany 2020 GDP = {v_deu:.2e}, expected ~3.9T. Formula or mapping error.")
    print(f"    Germany 2020 GDP = ${v_deu/1e12:.2f}T  PASS")
gdp_real.to_csv(PROC / "gdp_real_const2020.csv", index=False)
n_gdp_countries = gdp_real["iso3"].nunique()
print(f"    GDP-real series: {len(gdp_real):,} obs | {n_gdp_countries} countries")
print(f"    (Fix #2: not labelled 'global' — covers countries with UN-SDG data)")

print("  [V5] Population filter: identify countries pop < 1M")
wb_pop = wb[["iso3","year","population"]].dropna()
# For each EU country, check mean population in analysis window
eu_pop_check = (wb_pop[(wb_pop["iso3"].isin(EU27_ISO3)) &
                        (wb_pop["year"].between(START_YEAR, END_YEAR))]
                .groupby("iso3")["population"].mean())
small_eu = eu_pop_check[eu_pop_check < MIN_POP].index.tolist()
print(f"    EU countries with mean pop < {MIN_POP/1e6:.0f}M in {START_YEAR}–{END_YEAR}: {small_eu}")
print(f"    These will be EXCLUDED from ALL analyses (Fix #1)")

print("\n  ✓ All validation checks passed — proceeding to analysis")


# ══════════════════════════════════════════════════════════════════════════════
_phase(3, "ANALYTICAL DATASETS")
# ══════════════════════════════════════════════════════════════════════════════

# ── Fix #1: strict population filter applied upfront ──────────────────────────
print(f"\n  Applying population filter (pop < {MIN_POP/1e6:.0f}M excluded from all analyses)...")

def _eu_pop_ok(iso3_series, year_series):
    """Return boolean mask: True if country has pop >= MIN_POP in that year."""
    merged = pd.DataFrame({"iso3": iso3_series.values, "year": year_series.values})
    merged = merged.merge(wb_pop, on=["iso3","year"], how="left")
    return merged["population"].fillna(0) >= MIN_POP

# EU countries to exclude entirely
EXCLUDED_COUNTRIES = set(small_eu)
EU27_ANALYTICAL   = [c for c in EU27_ISO3 if c not in EXCLUDED_COUNTRIES]
print(f"  EU-27 analytical sample: {len(EU27_ANALYTICAL)} countries "
      f"(excluded: {sorted(EXCLUDED_COUNTRIES)})")

# ── Dataset A: EU core (CMUR + UNEP flows + population + real GDP) ─────────────
print("\n  Building Dataset A (EU analytical sample, strict window)...")
eu_cmur = eurostat[eurostat["iso3"].isin(EU27_ANALYTICAL)].copy()
eu_cmur["year"] = eu_cmur["year"].astype(int)

unep_dmc = unep[unep["flow_code"]=="DMC"][["iso3","year","value"]].rename(columns={"value":"dmc_t"})
unep_de  = unep[unep["flow_code"]=="DE" ][["iso3","year","value"]].rename(columns={"value":"de_t"})
unep_dmi = unep[unep["flow_code"]=="DMI"][["iso3","year","value"]].rename(columns={"value":"dmi_t"})
unep_imp = unep[unep["flow_code"]=="IMP"][["iso3","year","value"]].rename(columns={"value":"imp_t"})
unep_exp = unep[unep["flow_code"]=="EXP"][["iso3","year","value"]].rename(columns={"value":"exp_t"})
unep_lbl = unep[["country","iso3"]].drop_duplicates()

unep_wide = (unep_dmc
    .merge(unep_de,  on=["iso3","year"], how="outer")
    .merge(unep_dmi, on=["iso3","year"], how="outer")
    .merge(unep_imp, on=["iso3","year"], how="outer")
    .merge(unep_exp, on=["iso3","year"], how="outer"))

dset_a = (eu_cmur[["iso3","country_name","year","cmur"]]
    .merge(unep_wide, on=["iso3","year"], how="left")
    .merge(unep_lbl, on="iso3", how="left"))
dset_a["country"] = dset_a["country"].fillna(dset_a["country_name"])
dset_a = dset_a.merge(wb_pop, on=["iso3","year"], how="left")
dset_a = dset_a.merge(gdp_real[["iso3","year","gdp_real_const2020"]], on=["iso3","year"], how="left")

# Fix #1: apply population filter — drop rows where pop < MIN_POP
n_before_a = len(dset_a)
dset_a = dset_a[dset_a["population"].fillna(0) >= MIN_POP]
print(f"    Dataset A: {n_before_a} → {len(dset_a)} rows after pop filter")

dset_a = dset_a[["country","iso3","year","cmur","dmc_t","de_t","dmi_t","imp_t","exp_t",
                  "population","gdp_real_const2020"]].sort_values(["iso3","year"]).reset_index(drop=True)
dset_a.to_csv(PROC / "dataset_a_recycling_material.csv", index=False)
print(f"  [Dataset A] {len(dset_a):,} rows | {dset_a['iso3'].nunique()} EU countries | "
      f"{dset_a['year'].min()}–{dset_a['year'].max()}")

# ── Dataset B: Broader real-GDP decoupling (Fix #2 — honest labelling) ─────────
print("\n  Building Dataset B (broader decoupling, countries with real-GDP data)...")
dset_b = (unep_dmc
    .merge(unep_lbl, on="iso3", how="left")
    .merge(wb_pop,   on=["iso3","year"], how="left")
    .merge(gdp_real[["iso3","year","gdp_real_const2020"]], on=["iso3","year"], how="left"))
dset_b = dset_b[dset_b["dmc_t"] > 0]
# Fix #1: population filter
dset_b = dset_b[dset_b["population"].fillna(0) >= MIN_POP]
dset_b.to_csv(PROC / "dataset_b_decoupling.csv", index=False)
gdp_coverage = dset_b.dropna(subset=["gdp_real_const2020"])
print(f"  [Dataset B] {len(dset_b):,} rows | {dset_b['iso3'].nunique()} countries (pop≥1M)")
print(f"    Real-GDP coverage: {gdp_coverage['iso3'].nunique()} countries with UN-SDG GDP")
print(f"    NOTE (Fix #2): Not global — limited to countries with UN-SDG indicators")

print(f"\n  ✓ Phase 3 complete")


# ══════════════════════════════════════════════════════════════════════════════
_phase(4, "CORE INDICATORS — strict window 2010–2022")
# ══════════════════════════════════════════════════════════════════════════════

# Fix #8: strict common window — use exact endpoint years
def _compute_changes(df_in, iso3_list, y1=START_YEAR, y2=END_YEAR):
    """
    Compute country-level changes using strict start/end years y1 and y2.
    Fix #8: all countries use the same window; no country-specific first/last.
    Fix #3: corrected Tapio 8-state classification.
    """
    df = df_in[(df_in["year"].between(y1, y2)) &
               (df_in["iso3"].isin(iso3_list))].copy()
    # Derived variables (within window)
    df["dmc_pc"]  = df["dmc_t"]  / df["population"]
    df["de_pc"]   = df["de_t"]   / df["population"]
    df["dmc_gdp"] = df["dmc_t"]  / df["gdp_real_const2020"] * 1e6  # t per M USD
    df["de_gdp"]  = df["de_t"]   / df["gdp_real_const2020"] * 1e6
    df["gdp_pc"]  = df["gdp_real_const2020"] / df["population"]

    records = []
    for iso3, grp in df.groupby("iso3"):
        grp = grp.sort_values("year")
        country = grp["country"].dropna().iloc[0] if grp["country"].notna().any() else iso3

        cmur_i, cmur_f = _first_last_strict(grp, "cmur", y1, y2)
        dmc_i,  dmc_f  = _first_last_strict(grp, "dmc_t", y1, y2)
        de_i,   de_f   = _first_last_strict(grp, "de_t", y1, y2)
        dmi_i,  dmi_f  = _first_last_strict(grp, "dmi_t", y1, y2)
        imp_i,  imp_f  = _first_last_strict(grp, "imp_t", y1, y2)
        gdp_i,  gdp_f  = _first_last_strict(grp, "gdp_real_const2020", y1, y2)
        pop_i,  pop_f  = _first_last_strict(grp, "population", y1, y2)

        delta_cmur = (cmur_f - cmur_i) if not (pd.isna(cmur_i) or pd.isna(cmur_f)) else np.nan
        pct_dmc    = _pct(dmc_i, dmc_f)
        pct_de     = _pct(de_i, de_f)
        pct_dmi    = _pct(dmi_i, dmi_f)
        pct_imp    = _pct(imp_i, imp_f)
        pct_gdp    = _pct(gdp_i, gdp_f)

        dmc_pc_i  = (dmc_i / pop_i)  if (not pd.isna(dmc_i)  and not pd.isna(pop_i)  and pop_i  > 0) else np.nan
        dmc_pc_f  = (dmc_f / pop_f)  if (not pd.isna(dmc_f)  and not pd.isna(pop_f)  and pop_f  > 0) else np.nan
        pct_dmc_pc = _pct(dmc_pc_i, dmc_pc_f)

        dmc_gdp_i = (dmc_i / gdp_i * 1e6) if (not pd.isna(dmc_i) and not pd.isna(gdp_i) and gdp_i > 0) else np.nan
        dmc_gdp_f = (dmc_f / gdp_f * 1e6) if (not pd.isna(dmc_f) and not pd.isna(gdp_f) and gdp_f > 0) else np.nan
        pct_dmc_gdp = _pct(dmc_gdp_i, dmc_gdp_f)

        de_pc_i  = (de_i / pop_i)  if (not pd.isna(de_i)  and not pd.isna(pop_i)  and pop_i  > 0) else np.nan
        de_pc_f  = (de_f / pop_f)  if (not pd.isna(de_f)  and not pd.isna(pop_f)  and pop_f  > 0) else np.nan
        pct_de_pc = _pct(de_pc_i, de_pc_f)
        de_gdp_i = (de_i / gdp_i * 1e6) if (not pd.isna(de_i) and not pd.isna(gdp_i) and gdp_i > 0) else np.nan
        de_gdp_f = (de_f / gdp_f * 1e6) if (not pd.isna(de_f) and not pd.isna(gdp_f) and gdp_f > 0) else np.nan
        pct_de_gdp = _pct(de_gdp_i, de_gdp_f)

        # ── Fix #3: Tapio (2005) 8-state classification ─────────────────────
        # Reference: Tapio P. (2005) Towards a theory of decoupling: degrees
        # of decoupling in the EU and the case of road traffic in Finland
        # between 1970 and 2001. Transport Policy, 12(2), 137–151.
        # E = %ΔDMC / %ΔGDP  (elasticity of material use w.r.t. GDP)
        # Thresholds: 0.8 and 1.2 (Tapio 2005, Table 1)
        tapio_e     = np.nan
        tapio_class = "Insufficient data"
        if not (pd.isna(pct_gdp) or pd.isna(pct_dmc)):
            e = pct_dmc / pct_gdp if pct_gdp != 0 else np.nan
            tapio_e = e
            if pct_gdp > 0 and pct_dmc <= 0:
                tapio_class = "Strong decoupling"           # E < 0, GDP↑, DMC↓
            elif pct_gdp > 0 and pct_dmc > 0:
                if   pd.isna(e):          tapio_class = "Insufficient data"
                elif e < 0.8:             tapio_class = "Weak decoupling"
                elif e <= 1.2:            tapio_class = "Expansive coupling"
                else:                     tapio_class = "Expansive negative decoupling"
            elif pct_gdp < 0 and pct_dmc > 0:
                tapio_class = "Strong negative decoupling"  # E < 0, GDP↓, DMC↑
            elif pct_gdp < 0 and pct_dmc <= 0:
                if pd.isna(e):            tapio_class = "Insufficient data"
                elif 0 < e < 0.8:         tapio_class = "Weak negative decoupling"
                elif e <= 1.2:            tapio_class = "Recessive coupling"
                else:                     tapio_class = "Recessive decoupling"
                # Edge: if DMC also 0
                if pct_dmc == 0:          tapio_class = "Recessive coupling"
            elif pct_gdp == 0 and pct_dmc == 0:
                tapio_class = "No change"

        # ── GDP-based decoupling (separate from Tapio) ────────────────────────
        if not (pd.isna(pct_gdp) or pd.isna(pct_dmc)):
            if   pct_gdp > 0 and pct_dmc < 0:  dec = "Absolute decoupling"
            elif pct_gdp > 0 and pct_dmc >= 0:
                dec = "Relative decoupling" if (not pd.isna(pct_dmc_gdp) and pct_dmc_gdp < 0) else "No decoupling"
            elif pct_gdp < 0 and pct_dmc < 0:  dec = "GDP-fell + DMC fell"
            elif pct_gdp < 0 and pct_dmc >= 0: dec = "GDP-fell + DMC rose"
            else:                               dec = "Other"
        else:
            dec = "Insufficient data"

        # ── Quadrant (Fix #11: no causal claim) ─────────────────────────────
        def quad(dc, dm):
            if pd.isna(dc) or pd.isna(dm): return "Insufficient data"
            if dc > 0 and dm < 0:  return "CMUR increased / DMC decreased"
            if dc > 0 and dm > 0:  return "CMUR increased / DMC also increased"  # Fix #11
            if dc < 0 and dm < 0:  return "CMUR decreased / DMC decreased"
            return                         "CMUR decreased / DMC increased"

        recycling_trend = ("Increasing" if not pd.isna(delta_cmur) and delta_cmur > 0.5
                           else "Decreasing" if not pd.isna(delta_cmur) and delta_cmur < -0.5
                           else "Stable" if not pd.isna(delta_cmur) else "Insufficient data")

        records.append(dict(
            country=country, iso3=iso3, year_start=y1, year_end=y2,
            cmur_initial=cmur_i, cmur_final=cmur_f, delta_cmur=delta_cmur,
            recycling_trend=recycling_trend,
            dmc_initial_t=dmc_i, dmc_final_t=dmc_f, pct_delta_dmc=pct_dmc,
            de_initial_t=de_i, de_final_t=de_f, pct_delta_de=pct_de,
            dmi_initial_t=dmi_i, dmi_final_t=dmi_f, pct_delta_dmi=pct_dmi,
            imp_initial_t=imp_i, imp_final_t=imp_f, pct_delta_imp=pct_imp,
            gdp_real_initial=gdp_i, gdp_real_final=gdp_f, pct_gdp_growth=pct_gdp,
            dmc_pc_initial=dmc_pc_i, dmc_pc_final=dmc_pc_f, pct_delta_dmc_pc=pct_dmc_pc,
            dmc_gdp_initial=dmc_gdp_i, dmc_gdp_final=dmc_gdp_f, pct_delta_dmc_gdp=pct_dmc_gdp,
            de_pc_initial=de_pc_i, de_pc_final=de_pc_f, pct_delta_de_pc=pct_de_pc,
            de_gdp_initial=de_gdp_i, de_gdp_final=de_gdp_f, pct_delta_de_gdp=pct_de_gdp,
            tapio_elasticity=round(float(tapio_e), 4) if not pd.isna(tapio_e) else np.nan,
            tapio_classification=tapio_class,
            decoupling=dec,
            quadrant=quad(delta_cmur, pct_dmc),
        ))
    return pd.DataFrame(records)

# Main window: 2010–2022
df_work = dset_a.copy()
changes = _compute_changes(df_work, EU27_ANALYTICAL, START_YEAR, END_YEAR)
changes.to_csv(PROC / "country_changes_summary.csv", index=False)
print(f"\n  [Changes] {len(changes)} countries | window {START_YEAR}–{END_YEAR}")
print(f"  Decoupling: {changes['decoupling'].value_counts().to_dict()}")
print(f"  Tapio: {changes['tapio_classification'].value_counts().to_dict()}")
print(f"  Quadrant: {changes['quadrant'].value_counts().to_dict()}")
print(f"  ✓ Phase 4 complete")


# ══════════════════════════════════════════════════════════════════════════════
_phase(5, "DESCRIPTIVE STATISTICS + CORRELATIONS")
# ══════════════════════════════════════════════════════════════════════════════

df_analysis = dset_a[(dset_a["year"].between(START_YEAR, END_YEAR))].copy()
df_analysis["dmc_pc"]  = df_analysis["dmc_t"] / df_analysis["population"]
df_analysis["de_pc"]   = df_analysis["de_t"]  / df_analysis["population"]
df_analysis["dmc_gdp"] = df_analysis["dmc_t"] / df_analysis["gdp_real_const2020"] * 1e6
df_analysis["de_gdp"]  = df_analysis["de_t"]  / df_analysis["gdp_real_const2020"] * 1e6
df_analysis["gdp_pc"]  = df_analysis["gdp_real_const2020"] / df_analysis["population"]

def _desc_row(name, s):
    v = s.dropna()
    return {"Indicator": name, "N": len(v),
            "Missing%": round(s.isna().mean()*100, 1),
            "Mean": round(v.mean(), 3), "Median": round(v.median(), 3),
            "Std": round(v.std(), 3), "Min": round(v.min(), 3), "Max": round(v.max(), 3)}

desc = pd.DataFrame([
    _desc_row("CMUR (%)",                    df_analysis["cmur"]),
    _desc_row("DMC total (Mt)",              df_analysis["dmc_t"]/1e6),
    _desc_row("DE total (Mt)",               df_analysis["de_t"]/1e6),
    _desc_row("DMI total (Mt)",              df_analysis["dmi_t"]/1e6),
    _desc_row("Imports (Mt)",                df_analysis["imp_t"]/1e6),
    _desc_row("Exports (Mt)",                df_analysis["exp_t"]/1e6),
    _desc_row("Population (M)",              df_analysis["population"]/1e6),
    _desc_row("GDP real const2020 (B USD)",  df_analysis["gdp_real_const2020"]/1e9),
    _desc_row("DMC per capita (t/person)",   df_analysis["dmc_pc"]),
    _desc_row("DMC/GDP (t per M USD)",       df_analysis["dmc_gdp"]),
    _desc_row("DE per capita (t/person)",    df_analysis["de_pc"]),
    _desc_row("GDP per capita (USD)",        df_analysis["gdp_pc"]),
])
desc.to_csv(STAT / "descriptive_statistics.csv", index=False)
print("\n  Descriptive statistics:")
print(desc.to_string(index=False))

# ── Correlations ─────────────────────────────────────────────────────────────
print("\n  Correlations (pooled country-year, 2010–2022):")
corr_pairs = [
    ("CMUR vs DMC total [NOTE: mechanical link — DMC is in CMUR denominator]",        "cmur", "dmc_t"),
    ("CMUR vs DMC per capita [mechanical link partially remains — DMC still in CMUR]", "cmur", "dmc_pc"),
    ("CMUR vs Domestic Extraction [no mechanical link to CMUR]",                      "cmur", "de_t"),
    ("CMUR vs DE per capita [no mechanical link to CMUR]",                            "cmur", "de_pc"),
    ("CMUR vs DMC/GDP [NOTE: DMC appears in both CMUR and this ratio]",               "cmur", "dmc_gdp"),
    ("CMUR vs DE/GDP [preferred — DE has no mechanical link to CMUR]",                "cmur", "de_gdp"),
    ("CMUR vs DMI (DE+Imports) [DMI shares no direct link to CMUR]",                  "cmur", "dmi_t"),
]
corr_rows = []
for label, x, y in corr_pairs:
    sub = df_analysis[[x, y]].dropna()
    if len(sub) < 10:
        continue
    pr, pp = scipy_stats.pearsonr(sub[x], sub[y])
    sr, sp = scipy_stats.spearmanr(sub[x], sub[y])
    corr_rows.append({"Relationship": label, "N": len(sub),
                      "Pearson_r": round(pr, 4), "Pearson_p": round(pp, 4),
                      "Spearman_r": round(sr, 4), "Spearman_p": round(sp, 4)})
    print(f"    {label[:65]:<65} r={pr:+.3f} p={pp:.4f}")
corr_df = pd.DataFrame(corr_rows)
corr_df.to_csv(STAT / "correlation_analysis.csv", index=False)

# ── Country-level within-country correlations ─────────────────────────────────
cl_rows = []
for iso3, grp in df_analysis.groupby("iso3"):
    g = grp.dropna(subset=["cmur","dmc_pc"])
    if len(g) < 5:
        continue
    pr, pp = scipy_stats.pearsonr(g["cmur"], g["dmc_pc"])
    sr, sp = scipy_stats.spearmanr(g["cmur"], g["dmc_pc"])
    slope  = np.polyfit(g["cmur"], g["dmc_pc"], 1)[0] if len(g) > 2 else np.nan
    cl_rows.append({"country": EU_NAMES.get(iso3, iso3), "iso3": iso3,
                    "n_years": len(g), "slope_cmur_dmc_pc": round(slope, 4),
                    "pearson_r": round(pr, 4), "pearson_p": round(pp, 4),
                    "spearman_r": round(sr, 4), "spearman_p": round(sp, 4),
                    "direction": "Negative" if pr < 0 else "Positive"})
cl_df = pd.DataFrame(cl_rows).sort_values("pearson_r")
cl_df.to_csv(STAT / "country_level_correlations.csv", index=False)
print(f"\n  Country-level correlations saved ({len(cl_df)} countries)")
print(f"  ✓ Phase 5 complete")


# ══════════════════════════════════════════════════════════════════════════════
_phase(6, "ROBUSTNESS AND VALIDATION")
# ══════════════════════════════════════════════════════════════════════════════

# ── CMUR threshold sensitivity ────────────────────────────────────────────────
print("\n  CMUR threshold sensitivity (what counts as 'CMUR increased')...")
thresh_rows = []
for thresh in [0.0, 0.5, 1.0]:
    ch_up_t = changes[changes["delta_cmur"] > thresh]
    ch_dn_t = changes[changes["delta_cmur"] < -thresh]
    n_up = len(ch_up_t)
    n_dn = len(ch_dn_t)
    n_neutral = len(changes) - n_up - n_dn
    n_up_dmc_dn = (ch_up_t["pct_delta_dmc"] < 0).sum() if n_up else 0
    n_up_dmc_up = (ch_up_t["pct_delta_dmc"] > 0).sum() if n_up else 0
    thresh_rows.append({
        "Threshold_pp": thresh,
        "N_CMUR_up": int(n_up),
        "N_CMUR_neutral_band": int(n_neutral),
        "N_CMUR_down": int(n_dn),
        "Of_CMUR_up__DMC_fell": int(n_up_dmc_dn),
        "Of_CMUR_up__DMC_rose": int(n_up_dmc_up),
        "Note": ("Main threshold: any positive change" if thresh==0
                 else f"Sensitivity: only >{thresh}pp counts as 'increased'; >{thresh}pp negative as 'decreased'")
    })
    print(f"  Threshold>{thresh}pp: CMUR↑={n_up} (DMC↓={n_up_dmc_dn}, DMC↑={n_up_dmc_up}) | "
          f"neutral={n_neutral} | CMUR↓={n_dn}")
_save_csv(pd.DataFrame(thresh_rows), STAT, "cmur_threshold_sensitivity.csv")
print("  [Table] cmur_threshold_sensitivity.csv")

# ── OECD robustness ──────────────────────────────────────────────────────────
oecd_eu = oecd[oecd["iso3"].isin(EU27_ANALYTICAL)].copy()
oecd_eu["year"] = oecd_eu["year"].astype(int)
unep_eu_dmc = unep_dmc[unep_dmc["iso3"].isin(EU27_ANALYTICAL)].copy()
wb_pop_eu   = wb_pop[wb_pop["iso3"].isin(EU27_ANALYTICAL)]
rob2 = unep_eu_dmc.merge(wb_pop_eu, on=["iso3","year"], how="left")
rob2["unep_dmc_pc"] = rob2["dmc_t"] / rob2["population"]
oecd_pc = oecd_eu.rename(columns={"value":"oecd_dmc_pc"})
rob2 = rob2.merge(oecd_pc[["iso3","year","oecd_dmc_pc"]], on=["iso3","year"], how="inner")
rob2 = rob2[(rob2["unep_dmc_pc"]>0) & (rob2["oecd_dmc_pc"]>0)]
if len(rob2) > 5:
    pr_rob, pp_rob = scipy_stats.pearsonr(rob2["unep_dmc_pc"], rob2["oecd_dmc_pc"])
    rob2["abs_diff"] = (rob2["unep_dmc_pc"] - rob2["oecd_dmc_pc"]).abs()
    rob2["pct_diff"] = rob2["abs_diff"] / rob2["oecd_dmc_pc"] * 100
    _save_csv(pd.DataFrame({
        "Metric": ["N","Pearson_r","Pearson_p","Mean abs diff (t/person)",
                   "Mean % diff","Median % diff"],
        "Value":  [len(rob2), round(pr_rob,4), round(pp_rob,4),
                   round(rob2["abs_diff"].mean(),3),
                   round(rob2["pct_diff"].mean(),2),
                   round(rob2["pct_diff"].median(),2)]
    }), STAT, "oecd_robustness.csv")
    print(f"\n  OECD robustness: N={len(rob2)}, r={pr_rob:.4f}, p={pp_rob:.4f}")
    print(f"    Mean |UNEP - OECD| = {rob2['abs_diff'].mean():.3f} t/person")

# ── UN-SDG validation ─────────────────────────────────────────────────────────
sdg_pc_eu = unsdg[(unsdg["series_code"]=="EN_MAT_DOMCMPC") &
                  (unsdg["material_type"]=="ALP") &
                  (unsdg["iso3"].isin(EU27_ANALYTICAL))].copy()
sdg_pc_eu["year"] = sdg_pc_eu["year"].astype(int)
unep_eu_pc = unep_dmc[unep_dmc["iso3"].isin(EU27_ANALYTICAL)].merge(
    wb_pop_eu, on=["iso3","year"], how="left")
unep_eu_pc["unep_dmc_pc"] = unep_eu_pc["dmc_t"] / unep_eu_pc["population"]
sub13 = unep_eu_pc.merge(sdg_pc_eu[["iso3","year","value"]].rename(columns={"value":"sdg_dmc_pc"}),
                         on=["iso3","year"], how="inner")
sub13 = sub13[(sub13["unep_dmc_pc"]>0) & (sub13["sdg_dmc_pc"]>0)]
if len(sub13) > 5:
    r13, p13 = scipy_stats.pearsonr(sub13["unep_dmc_pc"], sub13["sdg_dmc_pc"])
    _save_csv(pd.DataFrame({"Metric":["N","Pearson_r","Pearson_p"],
                            "Value":[len(sub13), round(r13,4), round(p13,4)]
                           }), STAT, "unsdg_validation.csv")
    print(f"\n  UN-SDG validation: N={len(sub13)}, r={r13:.4f}")

# ── Outlier analysis — data-driven, no hard-coded countries ──────────────────
out_rows = []
for ind_col, ind_name in [("pct_delta_de", "% Change in DE"),
                          ("pct_delta_dmc", "% Change in DMC"),
                          ("pct_gdp_growth", "% GDP growth"),
                          ("delta_cmur", "Change in CMUR (pp)")]:
    if ind_col not in changes.columns:
        continue
    s = changes[ind_col].dropna()
    if len(s) < 5:
        continue
    zmean, zstd = s.mean(), s.std()
    z_all = (s - zmean) / zstd
    out_mask = z_all.abs() > 2.0  # z > 2 threshold
    for idx in s[out_mask].index:
        row = changes.loc[idx]
        out_rows.append({
            "Indicator": ind_name,
            "Country":   row.get("country", row["iso3"]),
            "iso3":      row["iso3"],
            "Value":     round(s[idx], 2),
            "Z_score":   round(z_all[idx], 2),
            "Mean":      round(zmean, 2),
            "SD":        round(zstd, 2),
            "Note":      "Retained in analysis — treated as a genuine structural observation",
        })
    if out_mask.sum():
        outlier_countries = changes.loc[s[out_mask].index, "country"].tolist()
        print(f"  Outliers in {ind_name} (|z|>2.0): {outlier_countries}")
_save_csv(pd.DataFrame(out_rows if out_rows else
             [{"Indicator": "All", "Country": "None", "iso3": "—",
               "Value": np.nan, "Z_score": np.nan, "Mean": np.nan,
               "SD": np.nan, "Note": "No outliers detected at |z|>2.0"}]
             ), STAT, "outlier_analysis.csv")

print(f"\n  ✓ Phase 7 complete")


# ══════════════════════════════════════════════════════════════════════════════
_phase(8, "ALL TABLES")
# ══════════════════════════════════════════════════════════════════════════════

# Recycling performance table
# NOTE: uses FULL Eurostat series (earliest available → latest available, up to 2024)
# for country-level CMUR trend analysis.  The main cross-country comparison uses
# the strict 2010–2022 window (see country_changes_summary.csv).  These two tables
# serve different purposes and intentionally use different endpoints.
rp_rows = []
for iso3, grp in eurostat[eurostat["iso3"].isin(EU27_ANALYTICAL)].groupby("iso3"):
    g = grp.sort_values("year").dropna(subset=["cmur"])
    if len(g) < 2:
        continue
    yr = g["year"].astype(int)
    ci, cf = g["cmur"].iloc[0], g["cmur"].iloc[-1]
    delta  = cf - ci
    sl     = np.polyfit(yr, g["cmur"], 1)[0] if len(g) > 2 else np.nan
    rp_rows.append({"country": EU_NAMES.get(iso3,iso3), "iso3": iso3,
                    "window": "Full Eurostat series (2010–2024)",
                    "year_initial": int(yr.iloc[0]), "year_final": int(yr.iloc[-1]),
                    "cmur_initial": round(ci,2), "cmur_final": round(cf,2),
                    "delta_cmur_pp": round(delta,2), "slope_pp_yr": round(sl,4),
                    "trend": "Increasing" if delta>0.5 else "Decreasing" if delta<-0.5 else "Stable",
                    "note": "Endpoint year varies by country (Eurostat data availability)"})
_save_csv(pd.DataFrame(rp_rows).sort_values("delta_cmur_pp", ascending=False),
          TABS, "recycling_performance.csv")
print("  [Table] recycling_performance.csv  [window: full Eurostat series 2010-2024]")

# Final results table (Fix #3: tapio now correct)
ft_cols = ["country","iso3","year_start","year_end","delta_cmur","pct_delta_dmc",
           "pct_delta_de","pct_delta_dmi","pct_delta_imp","pct_gdp_growth",
           "pct_delta_dmc_pc","pct_delta_dmc_gdp","pct_delta_de_pc","pct_delta_de_gdp",
           "decoupling","tapio_classification","tapio_elasticity","quadrant"]
ft = changes[[c for c in ft_cols if c in changes.columns]].sort_values(
    "delta_cmur", ascending=False, na_position="last")
for c in ft.select_dtypes(include=[float]).columns:
    ft[c] = ft[c].round(2)
_save_csv(ft, TABS, "final_results_table.csv")
if "final_results_table.xlsx" in MID_EVAL_TABLES:
    ft.to_excel(TABS/"final_results_table.xlsx", index=False)
print("  [Table] final_results_table.csv / .xlsx")

# Tapio classification table
tapio_tab = changes.groupby("tapio_classification").agg(
    n_countries=("iso3","count"),
    countries=("country", lambda x: ", ".join(x.dropna()))
).reset_index().sort_values("n_countries", ascending=False)
_save_csv(tapio_tab, TABS, "tapio_classification.csv")
print("  [Table] tapio_classification.csv")
print(tapio_tab.to_string(index=False))

# Decoupling table
dec_tab = changes.groupby("decoupling").agg(
    n_countries=("iso3","count"),
    countries=("country", lambda x: ", ".join(x.dropna()))
).reset_index().sort_values("n_countries", ascending=False)
_save_csv(dec_tab, TABS, "decoupling_table.csv")
print("  [Table] decoupling_table.csv")

# Quadrant table (Fix #11: correct labels)
quad_tab = changes.groupby("quadrant").agg(
    n_countries=("iso3","count"),
    countries=("country", lambda x: ", ".join(x.dropna()))
).reset_index().sort_values("n_countries", ascending=False)
_save_csv(quad_tab, TABS, "quadrant_classification.csv")
print("  [Table] quadrant_classification.csv")
print(quad_tab.to_string(index=False))

# Sensitivity summary (CMUR↑ countries across denominators, including DMI)
# Note: each row has its own interpretation note
METRIC_NOTES = {
    "Total DMC (UNEP)":
        "Production-based; does not capture consumption-side imports (material leakage possible)",
    "DMC per capita":
        "Per-capita indicator; same production-based limitation as Total DMC",
    "DMC/GDP":
        "Material intensity; improves with GDP growth even without absolute DMC reduction",
    "Domestic Extraction (UNEP)":
        "Measures extraction within borders only; not total consumption (no import footprint)",
    "DMI = DE+Imports (UNEP)":
        "Partially captures import leakage (DE + Imports); 12 of 19 CMUR-rising countries had rising DMI",
}
metrics = {"Total DMC (UNEP)": "pct_delta_dmc",
           "DMC per capita": "pct_delta_dmc_pc",
           "DMC/GDP": "pct_delta_dmc_gdp",
           "Domestic Extraction (UNEP)": "pct_delta_de",
           "DMI = DE+Imports (UNEP)": "pct_delta_dmi"}
ch_up = changes[changes["delta_cmur"] > 0].dropna(subset=["delta_cmur"])
sen_rows = []
for label, col in metrics.items():
    if col not in ch_up.columns:
        continue
    sub = ch_up.dropna(subset=[col])
    n_t = len(sub); n_d = (sub[col]<0).sum(); n_u = (sub[col]>0).sum()
    sen_rows.append({"Denominator": label, "Countries(CMUR↑)": n_t,
                     "AlsoDecline": n_d, "AlsoIncrease": n_u,
                     "%Decline": round(n_d/n_t*100,1) if n_t else np.nan,
                     "Note": METRIC_NOTES.get(label, "")})
_save_csv(pd.DataFrame(sen_rows), TABS, "sensitivity_analysis.csv")
print("  [Table] sensitivity_analysis.csv")

# Dataset inventory
inv = pd.DataFrame([
    {"Dataset":"UNEP","File":"UNEP.csv","Rows":len(unep),"Countries":unep["country"].nunique(),
     "Years":f"{unep['year'].min()}–{unep['year'].max()}","Indicators":"DE,DMC,DMI,IMP,EXP",
     "Units":"tonnes",
     "Notes":("Regional aggregates removed; UNKNOWN iso3 removed. "
              "2022–2024 values show near-zero cross-country spread in growth rates "
              "— possibly modelled/extrapolated; treat with caution.")},
    {"Dataset":"OECD","File":"OECD.csv","Rows":len(oecd),"Countries":oecd["iso3"].nunique(),
     "Years":f"{int(oecd['year'].min())}–{int(oecd['year'].max())}",
     "Indicators":"DMC per capita","Units":"t/person",
     "Notes":("Filtered to MEASURE=DMC, UNIT=Tonnes per person. Includes aggregates (W, OECD, EU27) "
              "and zeros/negatives — these are excluded by the EU-25 filter and the >0 check in the "
              "robustness comparison. Comparison uses all overlapping years (N=778), not restricted "
              "to the 2010–2022 analysis window.")},
    {"Dataset":"Eurostat","File":"EUROSTAT.csv","Rows":len(eurostat),"Countries":n_countries_eu,
     "Years":f"{int(eurostat['year'].min())}–{int(eurostat['year'].max())}",
     "Indicators":"CMUR (Circular Material Use Rate)","Units":"%",
     "Notes":("Single series verified; EL→GRC applied; EU27 aggregate excluded from analysis. "
              "Source of CMUR. Also source of DMC per capita for EU countries via UN-SDG series "
              "EN_MAT_DOMCMPC (24 of 25 countries; Germany from UNEP).")},
    {"Dataset":"UN-SDG","File":"UN-SDG.csv","Rows":len(unsdg),
     "Countries":unsdg["country_name"].nunique(),
     "Years":f"{int(unsdg['year'].min())}–{int(unsdg['year'].max())}",
     "Indicators":"DMC total,DMC/cap,DMC/GDP","Units":"tonnes; kg/USD",
     "Notes":("Used to derive real GDP (const 2020 USD) via: GDP = DMC_total / DMC_GDP_ratio. "
              "GDP validation is circular (checks formula consistency only). "
              "ALP validated vs components (median ratio=0.9992). "
              "DMC per capita series (EN_MAT_DOMCMPC) is Eurostat-sourced for EU countries.")},
    {"Dataset":"World Bank","File":"WORLDBANK-GDP.csv+POP.csv","Rows":len(wb),
     "Countries":wb["iso3"].nunique(),
     "Years":f"{wb['year'].min()}–{wb['year'].max()}",
     "Indicators":"GDP (current USD); Population","Units":"USD; persons",
     "Notes":("GDP in current USD only (not constant price) — used for supplementary reference only. "
              "Real GDP is derived from UN-SDG. Population used for per-capita calculations.")},
])
_save_csv(inv, TABS, "dataset_inventory.csv")
print("  [Table] dataset_inventory.csv")
print(f"\n  ✓ Phase 8 complete")


# ══════════════════════════════════════════════════════════════════════════════
_phase(9, "CASE STUDIES — data-driven selection (Fix #12)")
# ══════════════════════════════════════════════════════════════════════════════

# Fix #12: select case studies from actual results using explicit criteria
print("  Selecting case studies from actual results...")

ch_cs = changes.dropna(subset=["delta_cmur","pct_delta_dmc"]).copy()

criteria = {
    "CMUR↑ + DMC↓ (desirable pattern)":
        ch_cs[(ch_cs["delta_cmur"]>1) & (ch_cs["pct_delta_dmc"]<0)].nlargest(1,"delta_cmur"),
    "CMUR↑ + DMC↑ (recycling rose but so did DMC)":
        ch_cs[(ch_cs["delta_cmur"]>1) & (ch_cs["pct_delta_dmc"]>0)].nlargest(1,"pct_delta_dmc"),
    "Strong decoupling (Tapio)":
        ch_cs[ch_cs["tapio_classification"]=="Strong decoupling"].nlargest(1,"pct_gdp_growth"),
    "No / expansive coupling":
        ch_cs[ch_cs["tapio_classification"].isin(["No decoupling","Expansive coupling",
                                                   "Expansive negative decoupling"])].nlargest(1,"pct_delta_dmc"),
    "CMUR↑ + DE↓ (extraction fell)":
        ch_cs[(ch_cs["delta_cmur"]>1) & (ch_cs["pct_delta_de"]<0)].nlargest(1,"delta_cmur"),
    "GDP-fell case":
        ch_cs[ch_cs["decoupling"].str.startswith("GDP-fell")].nlargest(1,"pct_delta_dmc"),
}
case_list = []
seen = set()
for label, cand in criteria.items():
    for _, row in cand.iterrows():
        if row["iso3"] not in seen:
            seen.add(row["iso3"])
            case_list.append({"case_label": label, "country": row["country"], "iso3": row["iso3"]})
            break

if len(case_list) < 4:
    # Top by delta_cmur to fill
    for _, row in ch_cs.sort_values("delta_cmur", ascending=False).iterrows():
        if row["iso3"] not in seen and len(case_list) < 6:
            seen.add(row["iso3"])
            case_list.append({"case_label": "Top CMUR increase", "country": row["country"], "iso3": row["iso3"]})

case_countries = [c["iso3"] for c in case_list][:6]
print(f"  Selected case studies ({len(case_countries)}): {case_countries}")
for c in case_list:
    print(f"    {c['iso3']} ({c['country']}): {c['case_label']}")

cs_detail = []
for item in case_list:
    iso3 = item["iso3"]
    row  = changes[changes["iso3"]==iso3].iloc[0] if iso3 in changes["iso3"].values else {}
    if not isinstance(row, dict):
        row = row.to_dict()
    row_out = {"case_label": item["case_label"], "country": item["country"], "iso3": iso3}
    for k in ["cmur_initial","cmur_final","delta_cmur","pct_delta_dmc","pct_delta_de",
              "pct_gdp_growth","dmc_pc_initial","dmc_pc_final","pct_delta_dmc_pc",
              "pct_delta_dmc_gdp","tapio_classification","decoupling","quadrant"]:
        row_out[k] = row.get(k, np.nan)
    cs_detail.append(row_out)
cs_df = pd.DataFrame(cs_detail)
_save_csv(cs_df, TABS, "case_studies_detail.csv")
print("  [Table] case_studies_detail.csv")
print(f"\n  ✓ Phase 9 complete")


# ══════════════════════════════════════════════════════════════════════════════
_phase(10, "ALL FIGURES (15 MID-EVAL OUTPUTS)")
# ══════════════════════════════════════════════════════════════════════════════

eu_all = eurostat[eurostat["iso3"].isin(EU27_ANALYTICAL)].copy()
eu_all["year_int"] = eu_all["year"].astype(int)
eu27_agg = eurostat[eurostat["iso2"]=="EU27_2020"].sort_values("year")

# Representative country selection: spread evenly across the CMUR ranking
# (low, medium, high CMUR) so all parts of the distribution are visible.
cnt = eu_all.groupby("iso3")["cmur"].count()
top = cnt[cnt>=10].index.tolist()
avg = eu_all[eu_all["iso3"].isin(top)].groupby("iso3")["cmur"].mean().sort_values()
n_total = len(avg)
# Pick 2 from bottom tercile, 3 from middle, 3 from top — spans full range
q1 = n_total // 3; q2 = 2 * n_total // 3
bottom_group = list(avg.iloc[:q1].index)[:2]
middle_group = list(avg.iloc[q1:q2].index)[:3]
top_group    = list(avg.iloc[q2:].index)[:3]
sel = (bottom_group + middle_group + top_group)[:8]
print(f"  Representative countries (evenly spread across CMUR ranking): {sel}")

# ── Fig 1: CMUR trend ─────────────────────────────────────────────────────────
yr_g = eu_all.groupby("year_int")["cmur"]
mn, mx, med = yr_g.min(), yr_g.max(), yr_g.median()
yr_arr = mn.index.to_numpy().astype(int)
fig, ax = plt.subplots(figsize=(10,5))
ax.fill_between(yr_arr, mn.values, mx.values, alpha=0.12, color=PAL["blue"], label="Country range")
ax.plot(yr_arr, med.values, "--", color=PAL["blue"], lw=1.5, label="Median CMUR (EU analytical sample)")
if len(eu27_agg):
    ax.plot(eu27_agg["year"].astype(int).values, eu27_agg["cmur"].values,
            "-o", color=PAL["green"], lw=2.5, ms=5, label="EU27 aggregate (Eurostat)")
ax.set_xlabel("Year"); ax.set_ylabel("CMUR (%)")
ax.set_title("Fig 1 – Circular Material Use Rate (CMUR) Trend\n"
             f"EU Analytical Sample ({len(EU27_ANALYTICAL)} countries, Eurostat 2004–2024)  [Source: Eurostat]\n"
             "(Country-level series start from 2010; EU27 aggregate available from 2004)")
ax.legend(); ax.grid(axis="y", alpha=0.3)
_save(fig, "fig1_cmur_trend.png")

# ── Fig 2: CMUR ranking ───────────────────────────────────────────────────────
lc = eu_all.sort_values("year_int").groupby("iso3").last().reset_index()
lc = lc.sort_values("cmur", ascending=True)
lc["label"] = lc["iso3"].map(EU_NAMES).fillna(lc["iso3"])
c2 = [PAL["green"] if v>=10 else PAL["blue"] if v>=6 else PAL["orange"] for v in lc["cmur"]]
fig, ax = plt.subplots(figsize=(9,8))
bars = ax.barh(lc["label"], lc["cmur"], color=c2)
ax.axvline(lc["cmur"].mean(), color=PAL["red"], ls="--", lw=1.5, label=f"Mean {lc['cmur'].mean():.1f}%")
for bar, v in zip(bars, lc["cmur"]):
    ax.text(v+0.1, bar.get_y()+bar.get_height()/2, f"{v:.1f}", va="center", fontsize=8)
ax.set_xlabel("CMUR (%)"); ax.legend()
ax.set_title("Fig 2 – Country Ranking: CMUR (Latest Year)\n[Source: Eurostat; EU analytical sample]")
_save(fig, "fig2_cmur_ranking.png")

# ── Fig 3: CMUR trajectories ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10,6))
for i, iso3 in enumerate(sel):
    s = eu_all[eu_all["iso3"]==iso3].sort_values("year_int")
    ax.plot(s["year_int"], s["cmur"], "-o", label=EU_NAMES.get(iso3,iso3),
            color=CPAL[i%len(CPAL)], lw=2, ms=4)
ax.set_xlabel("Year"); ax.set_ylabel("CMUR (%)")
ax.set_title("Fig 3 – CMUR Trajectories: Selected EU Countries  [Source: Eurostat]")
ax.legend(bbox_to_anchor=(1.02,1), loc="upper left", fontsize=9); ax.grid(axis="y", alpha=0.3)
_save(fig, "fig3_cmur_trajectories.png")

# ── Fig 4: DMC trends ─────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10,5))
for i, iso3 in enumerate(sel):
    s = dset_a[dset_a["iso3"]==iso3].sort_values("year").dropna(subset=["dmc_t"])
    if s.empty: continue
    ax.plot(s["year"], s["dmc_t"]/1e6, "-", label=EU_NAMES.get(iso3,iso3),
            color=CPAL[i%len(CPAL)], lw=2)
ax.set_xlabel("Year"); ax.set_ylabel("DMC (million tonnes)")
ax.set_title("Fig 4 – DMC Trends: Selected EU Countries  [Source: UNEP]")
ax.legend(bbox_to_anchor=(1.02,1), loc="upper left", fontsize=9); ax.grid(axis="y", alpha=0.3)
_save(fig, "fig4_dmc_trends.png")

# ── Fig 5: CMUR change vs DMC change ─────────────────────────────────────────
cmap5 = {"Absolute decoupling": PAL["green"], "Relative decoupling": PAL["blue"],
         "No decoupling": PAL["orange"], "GDP-fell + DMC fell": PAL["purple"],
         "GDP-fell + DMC rose": PAL["red"], "Insufficient data": PAL["grey"]}
sub5 = changes.dropna(subset=["delta_cmur","pct_delta_dmc"]).copy()
sub5["label"] = sub5["iso3"].map(EU_NAMES).fillna(sub5["iso3"])
c5 = [cmap5.get(d, PAL["grey"]) for d in sub5["decoupling"]]
fig, ax = plt.subplots(figsize=(11,9))
ax.scatter(sub5["delta_cmur"], sub5["pct_delta_dmc"], c=c5, s=100, zorder=5,
           edgecolors="white", lw=0.5)
ax.axvline(0, color="black", lw=0.8); ax.axhline(0, color="black", lw=0.8)
xmx = sub5["delta_cmur"].abs().max()*0.55
ymx = sub5["pct_delta_dmc"].abs().max()*0.75
ax.text( xmx,  ymx, "CMUR↑ / DMC↑\n(DMC also rose)", color=PAL["orange"], fontsize=8, alpha=0.8, ha="center")
ax.text(-xmx,  ymx, "CMUR↓ / DMC↑\n(Unfavourable)", color=PAL["red"],    fontsize=8, alpha=0.8, ha="center")
ax.text( xmx, -ymx, "CMUR↑ / DMC↓\n(Desirable)",    color=PAL["green"],  fontsize=8, alpha=0.8, ha="center")
ax.text(-xmx, -ymx, "CMUR↓ / DMC↓",                 color=PAL["purple"], fontsize=8, alpha=0.8, ha="center")
for _, r in sub5.iterrows():
    ax.annotate(r["label"], (r["delta_cmur"], r["pct_delta_dmc"]),
                textcoords="offset points", xytext=(5,3), fontsize=7.5)
x5, y5 = sub5["delta_cmur"].values, sub5["pct_delta_dmc"].values
m5 = np.isfinite(x5) & np.isfinite(y5)
if m5.sum() > 3:
    cf5 = np.polyfit(x5[m5], y5[m5], 1)
    xf  = np.linspace(x5[m5].min(), x5[m5].max(), 100)
    ax.plot(xf, np.polyval(cf5, xf), "--", color=PAL["dark"], lw=1.5, label="OLS trend (pooled)")
patches5 = [mpatches.Patch(color=v, label=k) for k,v in cmap5.items() if "Insufficient" not in k]
ax.legend(handles=patches5, fontsize=8, loc="lower right")
ax.set_xlabel("Change in CMUR (percentage points, 2010–2022)")
ax.set_ylabel("% Change in DMC (2010–2022)")
ax.set_title("Fig 5 – Change in CMUR vs Change in DMC\n"
             "(25 EU countries, 2010–2022; DMC is mechanically related to CMUR — see methodology)",
             fontsize=11)
ax.grid(alpha=0.2)
_save(fig, "fig5_cmur_vs_dmc.png")

# ── Fig 6: CMUR vs DE change ──────────────────────────────────────────────────
sub6 = changes.dropna(subset=["delta_cmur","pct_delta_de"]).copy()
sub6["label"] = sub6["iso3"].map(EU_NAMES).fillna(sub6["iso3"])
fig, ax = plt.subplots(figsize=(10,8))
ax.scatter(sub6["delta_cmur"], sub6["pct_delta_de"], color=PAL["purple"],
           s=85, edgecolors="white", lw=0.5, zorder=5)
ax.axvline(0, color="black", lw=0.8); ax.axhline(0, color="black", lw=0.8)
xmx6 = sub6["delta_cmur"].abs().max()*0.55
ymx6 = sub6["pct_delta_de"].abs().max()*0.75
ax.text( xmx6,  ymx6, "CMUR↑ / DE↑", color=PAL["orange"], fontsize=8.5, alpha=0.7, ha="center")
ax.text(-xmx6,  ymx6, "CMUR↓ / DE↑", color=PAL["red"],    fontsize=8.5, alpha=0.7, ha="center")
ax.text( xmx6, -ymx6, "CMUR↑ / DE↓\n(Desirable)", color=PAL["green"], fontsize=8.5, alpha=0.7, ha="center")
ax.text(-xmx6, -ymx6, "CMUR↓ / DE↓", color=PAL["purple"], fontsize=8.5, alpha=0.7, ha="center")
for _, r in sub6.iterrows():
    ax.annotate(r["label"], (r["delta_cmur"], r["pct_delta_de"]),
                textcoords="offset points", xytext=(5,3), fontsize=7.5)
ax.set_xlabel("Change in CMUR (pp, 2010–2022)")
ax.set_ylabel("% Change in Domestic Extraction (2010–2022)")
ax.set_title("Fig 6 – CMUR Change vs Domestic Extraction Change\n"
             "(DE has no mechanical relationship to CMUR)  [Source: UNEP + Eurostat]")
ax.grid(alpha=0.2)
_save(fig, "fig6_cmur_vs_de.png")

# ── Fig 7: GDP vs DMC — decoupling ───────────────────────────────────────────
sub7 = changes.dropna(subset=["pct_gdp_growth","pct_delta_dmc"]).copy()
sub7["label"] = sub7["iso3"].map(EU_NAMES).fillna(sub7["iso3"])
c7 = [cmap5.get(d, PAL["grey"]) for d in sub7["decoupling"]]
fig, ax = plt.subplots(figsize=(10,8))
ax.scatter(sub7["pct_gdp_growth"], sub7["pct_delta_dmc"], c=c7, s=85,
           edgecolors="white", lw=0.5, zorder=5)
ax.axvline(0, color="black", lw=0.8); ax.axhline(0, color="black", lw=0.8)
for _, r in sub7.iterrows():
    ax.annotate(r["label"], (r["pct_gdp_growth"], r["pct_delta_dmc"]),
                textcoords="offset points", xytext=(5,3), fontsize=7.5)
ax.legend(handles=patches5, fontsize=8, loc="lower right")
ax.set_xlabel("% GDP Growth — real, const 2020 USD (2010–2022)")
ax.set_ylabel("% Change in DMC (2010–2022)")
ax.set_title("Fig 7 – GDP Growth vs DMC Change: Decoupling Classification\n"
             "(Real GDP = const 2020 USD derived from UN SDG)")
ax.grid(alpha=0.2)
_save(fig, "fig7_gdp_vs_dmc.png")

# ── Fig 8: Decoupling count ───────────────────────────────────────────────────
dc = changes["decoupling"].value_counts()
c8 = [cmap5.get(k, PAL["grey"]) for k in dc.index]
fig, ax = plt.subplots(figsize=(10,5))
bars8 = ax.barh(dc.index, dc.values, color=c8)
for bar, v in zip(bars8, dc.values):
    ax.text(v+0.05, bar.get_y()+bar.get_height()/2, str(v), va="center", fontsize=10)
ax.set_xlabel("Number of Countries")
ax.set_title("Fig 8 – Decoupling Classification\n"
             f"(EU analytical sample, {START_YEAR}–{END_YEAR}, real GDP const 2020 USD)")
ax.grid(axis="x", alpha=0.3)
_save(fig, "fig8_decoupling_counts.png")

# ── Fig 9: DMC per capita trends ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10,5))
for i, iso3 in enumerate(sel):
    s = dset_a[dset_a["iso3"]==iso3].sort_values("year").copy()
    s["dmc_pc"] = s["dmc_t"] / s["population"]
    s = s.dropna(subset=["dmc_pc"])
    if s.empty: continue
    ax.plot(s["year"], s["dmc_pc"], label=EU_NAMES.get(iso3,iso3), color=CPAL[i%len(CPAL)], lw=2)
ax.set_xlabel("Year"); ax.set_ylabel("DMC per capita (t/person)")
ax.set_title("Fig 9 – DMC per Capita Trends  [Source: UNEP + World Bank]")
ax.legend(bbox_to_anchor=(1.02,1), loc="upper left", fontsize=9); ax.grid(axis="y", alpha=0.3)
_save(fig, "fig9_dmc_per_capita.png")

# ── Fig 11: OECD vs UNEP validation ─────────────────────────────────────────
if len(rob2) > 5:
    r11, _ = scipy_stats.pearsonr(rob2["unep_dmc_pc"], rob2["oecd_dmc_pc"])
    fig, ax = plt.subplots(figsize=(7,6))
    ax.scatter(rob2["unep_dmc_pc"], rob2["oecd_dmc_pc"], alpha=0.4, color=PAL["blue"], s=20)
    lo = min(rob2["unep_dmc_pc"].min(), rob2["oecd_dmc_pc"].min())*0.9
    hi = max(rob2["unep_dmc_pc"].max(), rob2["oecd_dmc_pc"].max())*1.1
    ax.plot([lo,hi], [lo,hi], "k--", lw=1, label="1:1 line")
    ax.set_xlabel("UNEP DMC/cap (t)"); ax.set_ylabel("OECD DMC/cap (t)")
    ax.set_title(f"Fig 11 – UNEP vs OECD DMC/capita Cross-Source Comparison\n"
                 f"(EU-25 countries, all overlapping years; r={r11:.3f}, N={len(rob2):,})\n"
                 "Both sources measure DMC in t/person; median gap ~12% (different estimation methods)")
    ax.legend(); ax.grid(alpha=0.2)
    _save(fig, "fig11_oecd_vs_unep.png")

# ── Fig 12: Case studies (Fix #12: data-driven) ───────────────────────────────
if len(case_countries) >= 2:
    n_cases = min(len(case_countries), 6)
    ncols = 3; nrows = (n_cases + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(15, 5*nrows))
    axes_flat = axes.flatten() if n_cases > 1 else [axes]
    for idx, iso3 in enumerate(case_countries[:n_cases]):
        ax  = axes_flat[idx]; ax2 = ax.twinx()
        sd  = dset_a[dset_a["iso3"]==iso3].sort_values("year")
        se  = eu_all[eu_all["iso3"]==iso3].sort_values("year_int")
        lbl = next((c["case_label"] for c in case_list if c["iso3"]==iso3), iso3)
        if not sd.empty and sd["dmc_t"].notna().any():
            ax.plot(sd["year"], sd["dmc_t"]/1e6, "-o", color=PAL["blue"], ms=3, lw=1.8, label="DMC (Mt)")
        if not se.empty:
            ax2.plot(se["year_int"], se["cmur"].values, "-s", color=PAL["green"], ms=3, lw=1.8, label="CMUR (%)")
        ax.set_title(f"{EU_NAMES.get(iso3,iso3)}\n{lbl}", fontsize=9, fontweight="bold")
        ax.set_xlabel("Year", fontsize=8)
        ax.set_ylabel("DMC (Mt)", color=PAL["blue"], fontsize=8)
        ax2.set_ylabel("CMUR (%)", color=PAL["green"], fontsize=8)
        ax.tick_params(axis="y", labelcolor=PAL["blue"])
        ax2.tick_params(axis="y", labelcolor=PAL["green"])
        ax.spines["top"].set_visible(False)
        l1, lb1 = ax.get_legend_handles_labels()
        l2, lb2 = ax2.get_legend_handles_labels()
        ax.legend(l1+l2, lb1+lb2, fontsize=7, loc="upper left")
    for idx in range(n_cases, nrows*ncols):
        axes_flat[idx].set_visible(False)
    fig.suptitle("Fig 12 – Country Case Studies: DMC and CMUR Trajectories\n"
                 "(Data-driven selection; Source: UNEP DMC + Eurostat CMUR)\n"
                 "Note: Ireland GDP +140% driven by modified national accounts (MNI); "
                 "Greece DMC −57% driven by 2010 recession, not recycling",
                 fontsize=10)
    fig.tight_layout()
    _save(fig, "fig12_case_studies.png")

# ── Fig 17: DMC change bar ────────────────────────────────────────────────────
mc_s = changes.dropna(subset=["pct_delta_dmc"]).sort_values("pct_delta_dmc")
mc_s["label"] = mc_s["iso3"].map(EU_NAMES).fillna(mc_s["iso3"])
c17 = [PAL["green"] if v<0 else PAL["red"] for v in mc_s["pct_delta_dmc"]]
fig, ax = plt.subplots(figsize=(9,8))
bars = ax.barh(mc_s["label"], mc_s["pct_delta_dmc"], color=c17)
ax.axvline(0, color="black", lw=1)
for bar, v in zip(bars, mc_s["pct_delta_dmc"]):
    xp = v+0.5 if v>=0 else v-0.5
    ax.text(xp, bar.get_y()+bar.get_height()/2, f"{v:.1f}%",
            va="center", ha="left" if v>=0 else "right", fontsize=8)
ax.set_xlabel("% Change in DMC (2010–2022)")
ax.set_title("Fig 17 – % Change in DMC by Country (2010–2022)\n"
             "(Note: DMC also appears in the CMUR formula — see methodology)")
ax.grid(axis="x", alpha=0.3)
_save(fig, "fig17_dmc_change_bar.png")

# ── Fig 18: Quadrant count (Fix #11: corrected labels) ────────────────────────
qc = changes["quadrant"].value_counts()
cmap_q = {
    "CMUR increased / DMC decreased":  PAL["green"],
    "CMUR increased / DMC also increased": PAL["orange"],
    "CMUR decreased / DMC decreased":  PAL["purple"],
    "CMUR decreased / DMC increased":  PAL["red"],
    "Insufficient data":               PAL["grey"],
}
cq = [cmap_q.get(k, PAL["grey"]) for k in qc.index]
fig, ax = plt.subplots(figsize=(11,4))
bars = ax.bar(range(len(qc)), qc.values, color=cq, edgecolor="white", lw=0.5)
ax.set_xticks(range(len(qc)))
ax.set_xticklabels([k for k in qc.index], fontsize=9, rotation=15, ha="right")
for bar, v in zip(bars, qc.values):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.05, str(v),
            ha="center", va="bottom", fontweight="bold", fontsize=12)
ax.set_ylabel("Number of EU Countries"); ax.set_ylim(0, qc.max()+3)
ax.set_title("Fig 18 – CMUR vs DMC Quadrant Classification\n"
             "(25 EU countries, 2010–2022; no causality implied)")
ax.grid(axis="y", alpha=0.3)
_save(fig, "fig18_quadrant_classification.png")

# ── Fig 19: Tapio classification (Fix #3: corrected 8-state) ─────────────────
tc = changes["tapio_classification"].value_counts()
tapio_colors = {
    "Strong decoupling":               PAL["green"],
    "Weak decoupling":                 PAL["teal"],
    "Expansive coupling":              PAL["orange"],
    "Expansive negative decoupling":   PAL["red"],
    "Weak negative decoupling":        PAL["blue"],
    "Recessive coupling":              PAL["purple"],
    "Recessive decoupling":            PAL["dark"],
    "Strong negative decoupling":      PAL["dark"],
    "Insufficient data":               PAL["grey"],
}
ct = [tapio_colors.get(k, PAL["grey"]) for k in tc.index]
fig, ax = plt.subplots(figsize=(11,4))
bars = ax.bar(range(len(tc)), tc.values, color=ct, edgecolor="white", lw=0.5)
ax.set_xticks(range(len(tc)))
ax.set_xticklabels([k for k in tc.index], fontsize=8.5, rotation=20, ha="right")
for bar, v in zip(bars, tc.values):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.05, str(v),
            ha="center", va="bottom", fontweight="bold", fontsize=11)
ax.set_ylabel("Number of EU Countries")
ax.set_title("Fig 19 – Tapio Decoupling Elasticity Classification\n"
             "E = %ΔDMC / %ΔGDP  (Tapio 2005; 25 EU countries, 2010–2022)\n"
             f"States observed in data: {len(tc)} of 8 possible Tapio states")
ax.grid(axis="y", alpha=0.3)
_save(fig, "fig19_tapio_classification.png")

# ── Fig 23: CMUR vs DMI change ───────────────────────────────────────────────
sub23 = changes.dropna(subset=["delta_cmur","pct_delta_dmi"]).copy()
sub23["label"] = sub23["iso3"].map(EU_NAMES).fillna(sub23["iso3"])
if len(sub23) > 2:
    fig, ax = plt.subplots(figsize=(10,7))
    ax.scatter(sub23["delta_cmur"], sub23["pct_delta_dmi"], color=PAL["teal"],
               s=85, edgecolors="white", lw=0.5, zorder=5)
    ax.axvline(0, color="black", lw=0.8); ax.axhline(0, color="black", lw=0.8)
    for _, r in sub23.iterrows():
        ax.annotate(r["label"], (r["delta_cmur"], r["pct_delta_dmi"]),
                    textcoords="offset points", xytext=(5,3), fontsize=7.5)
    ax.set_xlabel("Change in CMUR (pp, 2010–2022)")
    ax.set_ylabel("% Change in DMI (Domestic Material Input = DE + Imports)")
    ax.set_title("Fig 23 – CMUR Change vs DMI Change\n"
                 "(DMI = DE + Imports; partially addresses import-leakage concern)")
    ax.grid(alpha=0.2)
    _save(fig, "fig23_cmur_vs_dmi.png")

print(f"\n{'='*66}")
print(f"  PIPELINE COMPLETE")
print(f"  Sample: {len(EU27_ANALYTICAL)} EU countries (excluded pop<1M: {sorted(EXCLUDED_COUNTRIES)})")
print(f"  Window: {START_YEAR}–{END_YEAR}")
print(f"  Figures  : {len(list(FIG.glob('*.png')))} in outputs/figures/")
print(f"  Tables   : {len(list(TABS.glob('*.*')))} in outputs/tables/")
print(f"  Statistics: {len(list(STAT.glob('*.*')))} in outputs/statistics/")
print(f"{'='*66}")
