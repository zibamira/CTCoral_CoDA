# Cora - The Coral Explorer

~ [Input](#input)
~ [Visualization](#visualization)
~ [ToDo](#todo)
~ [Usage](#usage)
~ [Rationale](#rationale)
~

This Python package implements *Cora - The Coral Explorer* application. An interactive link-and-brush tool with a real-time interface to Amira. It allows a fast visualization and exploration of cold-water corals, but doubles down as a general non-application specific explorative analysis tool.

## Usage

You just need a bunch of spreadsheets and otionally, some label fields. Cora distinguishes between two types of data:

*   **Vertex Data**\
    This data is given for each sample of your data. Usually, it is just a row in a spreadsheet.
*   **Edge Data**\
    This data links two vertices and contains features describing the relationship between the vertices. The resulting graph structure can be visualized in Cora.

You can pass the spreadsheets as command line arguments and launch the browser directly:
```property
$ python3 run.py --vertex label_analysis.csv --edge adjacency_graph.csv --vertex-field label_field.npy --start-browser
```
Cora will attempt to reload the dataframes every time a modification occurs.

## Amira

Amira makes it possible to export all relevant data as CSV spreadsheets or Numpy `.npy` files. Use the following modules to store your Amira data of interest automatic in an folder that is accessible by Cora.

*   **HxCoraVertexData** \
    Exports the attached Amira data object as *vertex* data.\
    Suports *HxLabelAnalysis*, *HxSpreadSheet* and *HxSpatialGraph*.
*   **HxCoraVertexDataFilter** \
    Filters the attached Amira data object based on the current Bokeh vertex selection.\
    Suports *HxLabelAnalysis*, *HxSpreadSheet* and *HxSpatialGraph*.
*   **HxCoraEdgeData** \
    Exports the attached Amira data object as *edge* data.\
    Suuports *HxLabelAnalysis*, *HxSpreadSheet* and *HxSpatialGraph*.
*   **HxCoraEdgeDataFilter** \
    Filters the attached Amira data object based on the current Bokeh edge selection.\
    Supports *HxSpatialGraph*.
*   **HxCoraGraph**
    Exports the attached Amira data object's edge *and* vertex attributes.\
    Supports *HxSpatialGraph*.

You must launch Cora *after* creating your first *Cora* module in Amira. Amira will create a temporary folder you can pass as command line argument to *Cora*.

```bash
$ ls /tmp | grep amira_cora_*
amira_cora_Untitled_c8vTVF
amira_cora_C1W_qz5qvv
$ python3 run.py --start-browser amira /tmp/amira_cora_Untitled_c8vTVF/ 
```

## Visualization

*   Spreadsheet
*   Histogram
*   Scatter
*   SPLOM
*   Graph
*   Map
*   Embedding
*   Flower

# Future

*   Fit a parabola curve to the Coral points clouds
    *   Implement a plane fit first
    *   Refine the rotation and curve parameters with a Gauss-Newton solver
    *   Output the polynomial coefficients as features, i.e. f'' as curvature,
        the path length and the mean distance to all points.   
*   Compute the buddy angle
    *   Compute the plane of the parabolas of the parent and child
    *   Compute the closest point of both parabolas, note that they
        don't need to intersect in general
    *   Compute the tangent of both parabolas at this point
    *   The angle between both tangents defines the buddy angle.
*   Fix the segmentation fault in the SaM shortest path computation
*   Compute the edge orientation
    *   Divide each label into "top" and "bottom"
    *   Check if the parabola intersects with the "top" or "bottom" 
        part of the parent.

## Nice To Have

*   Legends\
    Eventually add a legend for the color and marker factor maps. The rows in the 
    spreadsheet view could also be colored accordingly.
*   HistogramView\
    Add classical boxplot features like whiskers, min max
    and outlier views. 
*   ImageView and Thumbnails\
    Add a column to the data frame with the paths to images for each sample. The ImageView shows a grid with the thumbnails of the current selection and the thumbnails may also be attached to the hover tool.
*   3D Point Clouds\
    This could help to identify clusters in 3D, not relying only on 2D scatter plots.
*   Center Line Tree\
    Implement the Radius-Lifted center line trees.
*   Isomorphic 2D Graph Layout\ 
    Use the Buddy-Angles to create an isomorphic as possible 2D graph layout of the Coral framework.
*   Throttle/Debounce frequent updates\
    The histogram update in the SPLOM view must not necessarily be interactive, a short delay is ok. Similarly, the aggreagation in the FlowerView component may also be throttled. I think the best approach would be to create a global worker queue class (background thread) and a work queue. The views can push new jobs onto the worker and the worker schedules the "done" callback in the io loop. This worker could and should be used by the PCA, UMAP, Histogram and Flower views.
*   Propagate new columns\
    When a view, e.g. PCA or UMAP, add a new column to the dataframe, signalize the addition to other components so that they can update their UI.

## Rationale

This section contains some design rationales and also why I decided against some features.

*   **Filter Widgets**\
    Filter widgets usually work with range widgets or select menu. The range based filtering can be done with the BoxSelection tool and the select menu similarly in the scatter plot view. So it was not worth the trouble adding these widgets when they are not as easy to use. After all, the mouse tools allow for a better interactive approach.
*   **Delayed Updates and Reload**\
    Handling the reloading in a stable manner is a bit tricky. The multi-stage process looks roughly like this:
    *   The data provider detects a change and notifies the Cora application.
    *   An automatic reload is triggered or the user is notified.
    *   Cora sets the *is_reloading* flag to *True*.
    *   The data provider reloads the data.
    *   The views and helpers updated additional render information and store them in the data frames *df* and *df_edges.
    *   The Bokeh column data sources are updated with the content in the *df* and *df_edges* data frames.
    *   The views update the plots to account for the new data if needed.
    *   The reload is done and Cora sets the *is_reloading* flag to *False*.