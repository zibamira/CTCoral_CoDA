#!/bin/bash

python3 run.py\
    --vertex data/C1W/vertex_label_analysis.csv\
    --vertex data/C1W/vertex_mintree.csv\
	--vertex data/C1W/vertex_geo_location.csv\
    --edge data/C1W/edge_mintree.csv\
    --vertex-selection data/C1W/cora_vertex_selection.csv\
    --edge-selection data/C1W/cora_edge_selection.csv
