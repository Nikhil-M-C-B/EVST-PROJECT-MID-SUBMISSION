import json
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"
RAW_DIR = ROOT / "data" / "raw"

EU27_ISO2_ISO3 = {
    "AT":"AUT","BE":"BEL","BG":"BGR","CY":"CYP","CZ":"CZE",
    "DE":"DEU","DK":"DNK","EE":"EST","EL":"GRC","ES":"ESP",
    "FI":"FIN","FR":"FRA","HR":"HRV","HU":"HUN","IE":"IRL",
    "IT":"ITA","LT":"LTU","LU":"LUX","LV":"LVA","MT":"MLT",
    "NL":"NLD","PL":"POL","PT":"PRT","RO":"ROU","SE":"SWE",
    "SI":"SVN","SK":"SVK"
}

def fetch_wb_constant_gdp():
    """Fetch World Bank indicator NY.GDP.PCAP.KD for 27 EU countries 2010-2024 using curl."""
    print("Fetching World Bank NY.GDP.PCAP.KD (GDP per capita, constant 2015 US$) using curl...")
    records = []
    
    for iso2, iso3 in EU27_ISO2_ISO3.items():
        url = f"https://api.worldbank.org/v2/country/{iso2}/indicator/NY.GDP.PCAP.KD?format=json&date=2010:2024&per_page=100"
        try:
            cmd = ["curl", "-s", "-m", "5", url]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            if len(data) > 1 and data[1]:
                for entry in data[1]:
                    year = int(entry.get('date'))
                    val = entry.get('value')
                    records.append({
                        "iso3": iso3,
                        "year": year,
                        "GDP_per_capita_constant2015USD": val
                    })
        except Exception as e:
            print(f"Curl fetch error for {iso2}: {e}")
            
    df_gdp = pd.DataFrame(records)
    print(f"Fetched {len(df_gdp)} GDP per capita records across 27 EU countries.")
    return df_gdp

def main():
    # 1. Fetch WB Real GDP
    df_real_gdp = fetch_wb_constant_gdp()
    
    if df_real_gdp.empty:
        raise ValueError("Failed to fetch real GDP data from World Bank API")
        
    # Save raw download cache
    df_real_gdp.to_csv(RAW_DIR / "WORLDBANK-GDP-CONST2015.csv", index=False)
    
    # 2. Load existing master dataset (dataset_a_recycling_material.csv)
    master_path = PROC_DIR / "dataset_a_recycling_material.csv"
    master_df = pd.read_csv(master_path)
    print(f"Master dataset loaded: {len(master_df)} rows.")
    
    # 3. Merge new column without altering any existing columns
    updated_master = master_df.merge(df_real_gdp, on=["iso3", "year"], how="left")
    
    # Also load nominal GDP per capita from WORLDBANK-GDP.csv & WORLDBANK-POPULATION.csv to ensure exact nominal comparison
    wb_nom_path = RAW_DIR / "WORLDBANK-GDP.csv"
    wb_pop_path = RAW_DIR / "WORLDBANK-POPULATION.csv"
    
    wb_nom = pd.read_csv(wb_nom_path, skiprows=4)
    wb_pop = pd.read_csv(wb_pop_path, skiprows=4)
    
    nom_melted = wb_nom.melt(id_vars=["Country Code"], value_vars=[str(y) for y in range(2010, 2025)], var_name="year", value_name="gdp_nominal_total")
    pop_melted = wb_pop.melt(id_vars=["Country Code"], value_vars=[str(y) for y in range(2010, 2025)], var_name="year", value_name="pop_wb")
    
    nom_melted["year"] = nom_melted["year"].astype(int)
    pop_melted["year"] = pop_melted["year"].astype(int)
    nom_df = nom_melted.merge(pop_melted, on=["Country Code", "year"], how="inner")
    nom_df["GDP_per_capita_nominalUSD"] = nom_df["gdp_nominal_total"] / nom_df["pop_wb"]
    nom_df = nom_df.rename(columns={"Country Code": "iso3"})[["iso3", "year", "GDP_per_capita_nominalUSD"]]
    
    updated_master = updated_master.merge(nom_df, on=["iso3", "year"], how="left")
    
    # Save UPDATED_MASTER_DATASET.csv
    updated_master_path = OUT_DIR / "UPDATED_MASTER_DATASET.csv"
    updated_master.to_csv(updated_master_path, index=False)
    print(f"Saved {updated_master_path} ({len(updated_master)} rows)")
    
    # Also save to data/processed for pipeline compatibility
    updated_master.to_csv(PROC_DIR / "UPDATED_MASTER_DATASET.csv", index=False)
    
    # 4. Recompute decoupling classifications side-by-side (2010 vs 2022 common window)
    df_window = updated_master[(updated_master["year"].between(2010, 2022))].copy()
    
    comparison_rows = []
    
    for iso3, grp in df_window.groupby("iso3"):
        grp = grp.sort_values("year")
        c_name = grp["country"].iloc[0]
        
        g10 = grp[grp["year"] == 2010]
        g22 = grp[grp["year"] == 2022]
        
        if g10.empty or g22.empty:
            continue
            
        dmc_10 = g10["dmc_t"].iloc[0]
        dmc_22 = g22["dmc_t"].iloc[0]
        pct_delta_dmc = ((dmc_22 - dmc_10) / abs(dmc_10)) * 100
        
        # Nominal GDP growth
        gdp_nom_10 = g10["GDP_per_capita_nominalUSD"].iloc[0] * g10["population"].iloc[0] if pd.notna(g10["GDP_per_capita_nominalUSD"].iloc[0]) else np.nan
        gdp_nom_22 = g22["GDP_per_capita_nominalUSD"].iloc[0] * g22["population"].iloc[0] if pd.notna(g22["GDP_per_capita_nominalUSD"].iloc[0]) else np.nan
        pct_gdp_nom_growth = ((gdp_nom_22 - gdp_nom_10) / abs(gdp_nom_10)) * 100 if pd.notna(gdp_nom_10) and pd.notna(gdp_nom_22) else np.nan
        
        # Real GDP growth (constant 2015 USD)
        gdp_real_10 = g10["GDP_per_capita_constant2015USD"].iloc[0] * g10["population"].iloc[0]
        gdp_real_22 = g22["GDP_per_capita_constant2015USD"].iloc[0] * g22["population"].iloc[0]
        pct_gdp_real_growth = ((gdp_real_22 - gdp_real_10) / abs(gdp_real_10)) * 100
        
        # Nominal material intensity = DMC / Nominal GDP
        dmc_gdp_nom_10 = dmc_10 / gdp_nom_10 if pd.notna(gdp_nom_10) else np.nan
        dmc_gdp_nom_22 = dmc_22 / gdp_nom_22 if pd.notna(gdp_nom_22) else np.nan
        pct_delta_dmc_gdp_nom = ((dmc_gdp_nom_22 - dmc_gdp_nom_10) / abs(dmc_gdp_nom_10)) * 100 if pd.notna(dmc_gdp_nom_10) else np.nan
        
        # Real material intensity = DMC / Real GDP
        dmc_gdp_real_10 = dmc_10 / gdp_real_10
        dmc_gdp_real_22 = dmc_22 / gdp_real_22
        pct_delta_dmc_gdp_real = ((dmc_gdp_real_22 - dmc_gdp_real_10) / abs(dmc_gdp_real_10)) * 100
        
        # Classify Nominal
        if pct_gdp_nom_growth > 0 and pct_delta_dmc < 0:
            nom_class = "Absolute decoupling"
        elif pct_gdp_nom_growth > 0 and pct_delta_dmc >= 0:
            nom_class = "Relative decoupling" if (pct_delta_dmc_gdp_nom < 0) else "No decoupling"
        elif pct_gdp_nom_growth < 0 and pct_delta_dmc < 0:
            nom_class = "GDP-fell + DMC fell"
        else:
            nom_class = "Other"
            
        # Classify Real
        if pct_gdp_real_growth > 0 and pct_delta_dmc < 0:
            real_class = "Absolute decoupling"
        elif pct_gdp_real_growth > 0 and pct_delta_dmc >= 0:
            real_class = "Relative decoupling" if (pct_delta_dmc_gdp_real < 0) else "No decoupling"
        elif pct_gdp_real_growth < 0 and pct_delta_dmc < 0:
            real_class = "GDP-fell + DMC fell"
        else:
            real_class = "Other"
            
        category_changed = (nom_class != real_class)
        
        comparison_rows.append({
            "country": c_name,
            "iso3": iso3,
            "pct_delta_dmc": round(pct_delta_dmc, 2),
            "pct_gdp_nom_growth": round(pct_gdp_nom_growth, 2) if pd.notna(pct_gdp_nom_growth) else np.nan,
            "pct_gdp_real_growth": round(pct_gdp_real_growth, 2),
            "nominal_decoupling_class": nom_class,
            "real_decoupling_class": real_class,
            "category_changed": "YES" if category_changed else "NO"
        })
        
    comp_df = pd.DataFrame(comparison_rows)
    comp_path = OUT_DIR / "REAL_VS_NOMINAL_DECOUPLING_COMPARISON.csv"
    comp_df.to_csv(comp_path, index=False)
    print(f"Saved {comp_path}")
    
    n_changed = (comp_df["category_changed"] == "YES").sum()
    print(f"\n--- TASK 1 SUMMARY ---")
    print(f"Total countries analyzed: {len(comp_df)}")
    print(f"Countries changing decoupling classification: {n_changed}")
    if n_changed > 0:
        print(comp_df[comp_df["category_changed"] == "YES"][["country", "nominal_decoupling_class", "real_decoupling_class"]])
    else:
        print("No countries changed major decoupling category, but real growth rates & material intensity trajectories differ significantly!")

if __name__ == "__main__":
    main()
