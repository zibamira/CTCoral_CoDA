#!/usr/bin/env python3

"""
This script concatenates the analysis spreadsheets of multiple colonies
into a single dataframe so that they can be analyzed together.

Currently, it's just a workaround to see if it is feasible and useful.
"""

import pathlib
import collections

import numpy as np
import pandas as pd


this_dir = pathlib.Path(__file__).parent.absolute()
output_dir = this_dir / "data" / "inter_colony"
bremen_dir = (this_dir / "../BremenExploreScience").absolute()


# Add some meta data to the colonies themselves.
colony_infos = collections.OrderedDict()
colony_infos["A2W"] = {
    "latitude": 63.6077,
    "longitude": 9.3793,
    "elevation": -157.0,
    "data_dir": bremen_dir / "A2W"
}

# colony_infos["B2R"] = {
#     "latitude": 0.0,
#     "longitude": 0.0,
#     "elevation": 0.0
# }

colony_infos["C1W"] = {
    "latitude": 64.1110,
    "longitude": 8.1187,
    "elevation": -303.0,
    "data_dir": bremen_dir / "C1W"
}

colony_infos["SaM-43148"] = {
    "latitude": 41.719670,
    "longitude": 17.060830,
    "elevation": -700.0,
    "data_dir": bremen_dir / "SaM-43148"
}

colony_infos["GeoB12747-1"] = {
    "latitude": 34.98833,
    "longitude": -7.07200,
    "elevation": -714.0,
    "data_dir": bremen_dir / "GeoB12747-1"
}

colony_infos["Niwa-148046"] = {
    "latitude": -43.369,
    "longitude": 179.452,
    "elevation": 394.0,
    "data_dir": bremen_dir / "Niwa-148046"
}


# Merge all "calices.csv" spreadsheets into one.
prefixes = []
dfs_calices = []
dfs_corallites = []
dfs_framework = []
dfs_info = []

for name, info in colony_infos.items():
    df_calices = pd.read_csv(info["data_dir"] / "calices.csv", header=1)
    df_corallites = pd.read_csv(info["data_dir"] / "corallites.csv", header=1)
    # df_framework = pd.read_csv(info["data_dir"] / "framework.csv", header=1)
    
    # if "Node.label" in df_framework:
    #     df_framework["Node.Label"] = df_framework["Node.label"]

    nrows = len(df_calices.index)
    if len(df_calices.index) != nrows:
        print(f"{name} calices has incosistent number of rows {len(df_calices.index)}, expected {nrows}.")
    if len(df_corallites.index) != nrows:
        print(f"{name} corallites has incosistent number of rows {len(df_corallites.index)}, expected {nrows}.")
    # if len(df_framework.index) != nrows:
    #     print(f"{name} framework has incosistent number of rows {len(df_framework.index)}, expected {nrows}.")

    df_info = pd.DataFrame.from_dict({
        "latitude": [info["latitude"] for i in range(nrows)],
        "longitude": [info["longitude"] for i in range(nrows)],
        "elevation": [info["elevation"] for i in range(nrows)],
        "name": [name for i in range(nrows)],
        "idx_colony": [len(dfs_calices) for i in range(nrows)]
    })

    prefix = f"{name:}"

    prefixes.append(prefix)
    dfs_calices.append(df_calices)
    dfs_corallites.append(df_corallites)
    # dfs_framework.append(df_framework)
    dfs_info.append(df_info)


# Check if we need to get rid of some columns.
columns_calices = set.intersection(*[set(df.columns) for df in dfs_calices])
columns_corallites = set.intersection(*[set(df.columns) for df in dfs_corallites])
# columns_framework = set.intersection(*[set(df.columns) for df in dfs_framework])
columns_info = set.intersection(*[set(df.columns) for df in dfs_info])

# Give a warning when we remove a column.
for prefix, df in zip(prefixes, dfs_calices):
    missing_columns = set(df.columns) - columns_calices
    if missing_columns:
        print(f"The calices dataframe for '{prefix}' misses the following columns: {missing_columns}")

for prefix, df in zip(prefixes, dfs_corallites):
    missing_columns = set(df.columns) - columns_corallites
    if missing_columns:
        print(f"The corallites dataframe for '{prefix}' misses the following columns: {missing_columns}")

for prefix, df in zip(prefixes, dfs_framework):
    missing_columns = set(df.columns) - columns_framework
    if missing_columns:
        print(f"The framework dataframe for '{prefix}' misses the following columns: {missing_columns}")

for prefix, df in zip(prefixes, dfs_info):
    missing_columns = set(df.columns) - columns_info
    if missing_columns:
        print(f"The info dataframe for '{prefix}' misses the following columns: {missing_columns}")

# Sort the columns by name.
columns_calices = list(sorted(columns_calices))
columns_corallites = list(sorted(columns_corallites))
# columns_framework = list(sorted(columns_framework))
columns_info = list(sorted(columns_info))

# Concatenate all dataframes.
df_calices = pd.concat(df[columns_calices] for prefix, df in zip(prefixes, dfs_calices))
df_corallites = pd.concat(df[columns_corallites] for prefix, df in zip(prefixes, dfs_corallites))
# df_framework = pd.concat(df[columns_framework] for prefix, df in zip(prefixes, dfs_framework))
df_info = pd.concat(df[columns_info] for prefix, df in zip(prefixes, dfs_info))

# Save the compiled spreadsheets.
with (output_dir / "vertex_calices.csv").open("w") as file:
    file.write("\"CORA compilation\"\n")
    df_calices.to_csv(file, sep=",", header=True, index=False)

with (output_dir / "vertex_corallites.csv").open("w") as file:
    file.write("\"CORA compilation\"\n")
    df_corallites.to_csv(file, sep=",", header=True, index=False)

# with (this_dir / "data" / "vertex_framework.csv").open("w") as file:
#     file.write("\"CORA compilation\"\n")
#     df_framework.to_csv(file, sep=",", header=True, index=False)

with (output_dir / "vertex_info.csv").open("w") as file:
    file.write("\"CORA compilation\"\n")
    df_info.to_csv(file, sep=",", header=True, index=False)