#!/bin/bash

python3 run.py\
    --vertex data/C1W/vertex_label_analysis.csv\
    --vertex data/C1W/vertex_mintree.csv\
	--vertex data/C1W/vertex_geo_location.csv\
    --edge data/C1W/edge_mintree.csv\
    --vertex-field data/C1W/vertex_field.npy
