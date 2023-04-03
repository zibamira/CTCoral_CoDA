# py_cora

This Python package implements *Cora - The Coral Explorer* application. An interactive link-and-brush tool with a real-time interface to Amira. It allows a fast visualization and exploration of cold-water corals, but may also be used for other data.

## Input

*   Polyp Instance Segmentation\
    *HxUniformLabelField3*
*   Polyp Label Field Anlysis + Other Features\
    *HxSpreadSheet*
*   Label Field indicating if a Polyp is segmented correct or not. This field is used to guide the dimensionality reduction and give the user a visual feedback about clusters with wrong segmentations. \
    *HxUniformLabelField3*
*   Coral Framework
    *HxSpatialGraph*

## Visualization

*   Scatter Plots\
    The user can select and configure a scatter plot with all features.
*   Dimensionality Reduction\
    A UMAP dimension reduction is perfomed when one of the inputs change
    and updated automatic in the frontend. The features are visualized in 
    a scatter plot. 

## ToDo


*   Blockers:  
    *   Can I replace the colormap at runtime without a page reload?
    *   Can I replace the glyphmap at runtime without a page reload?
    *   Can I replace the graph layout without replaceing the plot?
    *   Can I add or remove plots to the SPLOM?
*   UI Widgets
    *   Add widgets for selecting the glyph label field
    *   Add widgets for selecting the color label field
    *   Add widgets for selecting the features used in UMap
    *   Add widgets for selecting the features shown in the SPLOM plot
    *   Add widgets for recomputing the spring layout
    *   Adjustable size of the vertex glyphs in the graph plot.
*   Link and Brush
    *   Use a single data source whenever possible
        *   Features (id -> features)
        *   Graph (id -> vertex attributes)
        *   Cluster (id -> component)
    *   Add a watchdog to the Python py_ipc package
    *   Add an ROI seeking function to the Amira hx_shmem package so that
        we can jump to the 3D location when a single instance is selected
        in Bokeh (New Bokeh Tool)
*   Graph   
    *   Add a recompute button for the spring layout
    *   Add a save button for the currently shown layout, i.e. the vertex positions.
    *   Add a button for selecting the current connected component if there 
        are multiple available
    *   Color the edges depending on their orienation, e.g.
        black: top -> bottom, everything else red
    *   Add a selection tool and link it with other views
    *   Add the (connected) component id to the vertex attributes
    *   Add a flag as vertex attribute: "root" or "descendant"
    *   Add an edge attribute: "orientation" giving a heuristic value if the edge is oriented correctly. Some value between 0 and 1.
*   Flower Glyph    
    *   Summarize the current selection 
    *   Flower or Star Glyph, or something similar to the visualization in the Antrag
*   Map visualization
    *   Location of the dataset on a world map

## ToDo Next

*   Combine all dataframes into a single Bokeh source
*   Link everything together (syncable = True)
*   Factor out the colormaps and share them
*   Factor out the glyphmaps and share them

## Usage

Please take a look at the [examples/](./examples) folder for examples. You should already be familiar with NumPy.