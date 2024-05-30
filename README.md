# Coda - The Codal Explorer

~ [Installation](#installation)
~ [Usage](#usage)
~ [Amira](#amira)
~ [Visualization](#visualization)
~ [Custom Tools](#custom-tools)
~ [Nice to Have](#nice-to-have)
~ [Rationale](#rationale)
~ [ToDo](#todo)
~

This Python package implements *Coda - The Codal Explorer* application. An interactive link-and-brush tool with a real-time interface to Amira. It allows a fast visualization and exploration of cold-water corals, but doubles down as a general non-application specific explorative analysis tool.


## Installation

Coda requires some external tools and libraries which must be installed first.
```property
$ apt install python3 python3-pip git graphviz
```

The easiest way to get started is by installing Coda into your local Python environment. 
```property
$ pip3 install --user https://github.com/AdorablePotato/coda
```

You can check if everything worked by starting Coda with some random data.
```property
$ python3 -m coda --start-browser random
```


## Usage

Coda was made for visualizing attributes defined on a graph. In a coral colony, the graph describes the framework. A coral (calice + corallite) would be a vertex and the connections describing ancestry the edges. A vertex could, for example, have a volume, length and weight attribute. Similarly, the edges may store the angle between parent and child, the length between both and the distances between them.

Now, get your spreadsheets and perhaps some label fields ready. Coda distinguishes between two types of data:
*   **Vertex Data**\
    This data is given for each sample of your data. Usually, it is just a row in a spreadsheet.
*   **Edge Data**\
    This data links two vertices and contains features describing the relationship between the vertices. The resulting graph structure can be visualized in Coda.

You can pass the spreadsheets as command line arguments and launch the browser directly:
```property
$ python3 run.py --vertex label_analysis.csv --edge adjacency_graph.csv --vertex-field label_field.npy --start-browser
```

Coda will attempt to reload the dataframes automatic every time a modification occurs. Eventually, you can reload manually by using the *Reload* button in the Browser UI.


## Amira

Amira makes it possible to export all relevant data as CSV spreadsheets or Numpy `.npy` files with the *HxCoda* package. Use the following modules to store your Amira data of interest automatic in an folder that is accessible by Coda.

*   **Coda Vertex (HxCodaVertexData)** \
    Exports the attached Amira data object as *vertex* data.\
    Suports *HxLabelAnalysis*, *HxSpreadSheet* and *HxSpatialGraph*.
*   **Coda Vertex Filter (HxCodaVertexDataFilter)** \
    Filters the attached Amira data object based on the current Bokeh vertex selection.\
    Suports *HxLabelAnalysis*, *HxSpreadSheet* and *HxSpatialGraph*.
*   **Coda Edge (HxCodaEdgeData)** \
    Exports the attached Amira data object as *edge* data.\
    Suuports *HxLabelAnalysis*, *HxSpreadSheet* and *HxSpatialGraph*.
*   **Coda Edge Filter (HxCodaEdgeDataFilter)** \
    Filters the attached Amira data object based on the current Bokeh edge selection.\
    Supports *HxSpatialGraph*.
*   **Coda Graph (HxCodaGraph)**
    Exports the attached Amira data object's edge *and* vertex attributes.\
    Supports *HxSpatialGraph*.

You can launch Coda either directly from within Amira by using the *Launch* button in one of these modules. 

If that does not work, you can still connect manually. Amira will create a temporary folder where all exported spreadsheets are stored. This folder is visible in any of the *hxcoda* modules. Copy the path and launch Coda:

```bash
$ ls /tmp | grep amira_coda_*
amira_coda_Untitled_c8vTVF
amira_coda_C1W_qz5qvv
$ python3 run.py --start-browser amira /tmp/amira_coda_Untitled_c8vTVF/ 
```


## Visualization

Coda is based on the Bokeh visualization framework and provides an extensive, interactive linke and brushing UI. You can choose between several visualizations:

*   **Spreadsheet**\
    Shows the raw data in a spreadsheet.
*   **Histogram**\
    Aggregates the data in a histogram. 2D histograms are possible.
*   **Scatter**\
    Shows a scatter plot of two columns in the spreadsheets.
*   **SPLOM (Scatter Plot Matrix)**\
    Shows a matrix of scatter plots (subfigure) of multiple columns.
*   **Graph**\
    Computes a graph layout and shows it. This visualization requires the *graphviz* library. 
*   **Map**\
    If you vertex data contains *latitude* and *longitude* columns, then they are shown on a world map.
*   **Embedding**\
    The embedding view provides a principal-component analysis tool (PCA) and a *UMAP* tool for dimensionality reduction. You can choose which columns should be part of the reduction and visualize the result in e.g. a Scatter plot. The reduction coefficients are made available as standard vertex attributes.
*   **Flower**\
    One of the more beautiful plots. A *flower* plots aggregates some statistics of user selected columns, e.g. the minimum, maximum, mean median and standard variance. These statistics are displayed in visually appealing flower like glyphs.
*   **Statistics**\
    Shows a spreadsheet with simple statistics (min, max, mean, quantiles, unique values), for the current selection. The statistics are shown for each scalar column in the original vertex spreadsheets.


## Custom Tools

Coda comes with custom Bokeh tools that are implemented via JavaScript, so that they will run in the frontend rather than the backend. The usage requires that the user has a NodeJs 14.0 or higher installed.

You can use NVM (Node Version Manager) to make sure that you have a compatible version installed. The LTS version should work but if you experience problems, then you may need to check BokehJs for it's latest compatible version and use that one.
```
nvm install --lts
nvm use --lts
```


## Nice To Have

Some things did not make it into Coda yet. 

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
*   Isomorphic 2D Graph Layout\ 
    Use the Buddy-Angles to create an isomorphic as possible 2D graph layout of the Codal framework.
*   Throttle/Debounce frequent updates\
    The histogram update in the SPLOM view must not necessarily be interactive, a short delay is ok. Similarly, the aggreagation in the FlowerView component may also be throttled. I think the best approach would be to create a global worker queue class (background thread) and a work queue. The views can push new jobs onto the worker and the worker schedules the "done" callback in the io loop. This worker could and should be used by the PCA, UMAP, Histogram and Flower views.
*   Propagate new columns\
    When a view, e.g. PCA or UMAP, add a new column to the dataframe, signalize the addition to other components so that they can update their UI.
*   A LICENSE file
*   A CITATION.cff file


## Rationale

This section contains some design rationales and also why I decided against some features.

*   **Why No Filter Widgets?**\
    Filter widgets usually work with range widgets or select menu. The range based filtering can be done with the BoxSelection tool and the select menu similarly in the scatter plot view. So it was not worth the trouble adding these widgets when they are not as easy to use. After all, the mouse tools allow for a better interactive approach.
*   **Reloading and Delayed Update Process**\
    Handling the reloading in a stable manner is a bit tricky. The multi-stage process looks roughly like this:
    *   The data provider detects a change and notifies the Coda application.
    *   An automatic reload is triggered or the user is notified.
    *   Coda sets the *is_reloading* flag to *True*.
    *   The data provider reloads the data.
    *   The views and helpers updated additional render information and store them in the data frames *df* and *df_edges.
    *   The Bokeh column data sources are updated with the content in the *df* and *df_edges* data frames.
    *   The views update the plots to account for the new data if needed.
    *   The reload is done and Coda sets the *is_reloading* flag to *False*.

