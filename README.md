# Coda - The Codal Explorer

~ [Installation](#installation)
~ [Usage](#usage)
~ [Amira](#amira)
~ [Visualization](#visualization)
~ [Custom Tools](#custom-tools)
~ [Nice to Have](#nice-to-have)
~ [ToDo](#todo)
~ [Rationale](#rationale)
~ [License](#license)
~

This Python package implements *CoDA - The Coral Dendroid Structure Analyzer* application. 
An interactive link-and-brush tool with a real-time interface to Amira. 
It allows a fast visualization and exploration of cold-water corals (CWC), but doubles down as a general non-application specific explorative analysis tool.
A simple, open source 3D viewer based on [PyVista](https://docs.pyvista.org/) is available in our [CoDA-PyVista](https://github.com/zibamira/CTCoral_CoDA_PyVista) repository.

Please cite the following preprint if you are using CoDA in your research:
>   https://doi.org/10.48550/arXiv.2406.18236

![CoDA gallery](docs/coda_gallery.png)


## Installation

CoDA requires some external tools and libraries which must be installed first.
```shell
$ sudo apt install python3 python3-pip git graphviz
```

The easiest way to get started is by installing CoDA into your local Python environment. 
```shell
$ pip3 install --user https://github.com/zibamira/CTcoral_CoDA
```

You can check if everything worked by starting CoDA with some random data.
```shell
$ python3 -m coda --start-browser random
```


## Usage

CoDA was made for visualizing attributes defined on a graph. 
In a coral colony, the graph describes the mother-daughter relationships.
A coral (calice/corallite) is represented by a vertex and the directed edges point from mother corallite/calyx to daughter corallite/calyx.

The vertices and edges are annotated with features computed for the associated objects.
For example, a vertex could have a volume, length and weight attribute. 
Similarly, the edges may store the angle between parent and child, the length between both and the distances between their centers.

CoDA distinguishes between two types of data:
*   **Vertex Data**\
    The vertex data is given by one or multiple *.csv* spreadsheets.
    You can combine multiple spreadsheets as long as they have the same number of rows.
    A vertex in two spreadsheets is the same if the row index is the same.
*   **Edge Data**\
    Similarly to the vertex data, edge data is given by one or multiple *.csv* spreadsheets.
    You can combine multiple spreadsheets as long as they have the same number of rows, i.e. the same number of edges.
    An edge in two spreadsheets is the same if the row index is the same.
    At least one spreadsheet should have a *start* (source id) column with the row index of the start vertex and an *end* (target id) column with the row index of the end vertex.
    Within CoDa, the resulting graph can be visualized using the *Graphviz* library.

You can pass the respective spreadsheets as command line arguments and launch the browser directly:
```shell
$ python3 -m coda --start-browser filesystem
    --vertex data/A2W/vertex_calices.Label-Analysis.csv
    --vertex data/A2W/vertex_corallites.Label-Analysis.csv
    --edge data/A2W/edge_framework.am.csv
```

CoDA will attempt to reload the spreadsheets automatic every time a modification occurs. 
Eventually, you can reload manually by using the *Reload* button in the Browser UI.


## Amira

Amira makes it possible to export all relevant data as CSV spreadsheets or Numpy `.npy` files with the [hxcoda](https://github.com/zibamira/CTcoral_hxcoda) package. 
The package is available in the *Amira ZIBEdition*.
Use the following modules to store your Amira data of interest automatic in an folder that is accessible by CoDA.

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

You can launch CoDA either directly from within Amira by using the *Launch* button in one of these modules. 

If that does not work, you can still connect manually. 
Amira will create a temporary folder where all exported spreadsheets are stored. 
This folder is visible in any of the *hxcoda* modules. 
You can copy the path and provide it explicitly to CoDa.
```shell
> ls /tmp | grep amira_coda_*
amira_coda_Untitled_c8vTVF
> python3 -m coda --start-browser amira --directory /tmp/amira_coda_Untitled_c8vTVF/ 
```

You can also let CoDA guess the shared folder automatic:
However, this may not work properly if you have multiple Amira instances running.
```shell
> python3 -m coda -start-browser amira
```


## Visualization

CoDA is based on the Bokeh visualization framework and provides an extensive, interactive linke and brushing UI. 
You can choose between several visualizations:

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

CoDA comes with custom Bokeh tools that are implemented via JavaScript, so that they will run in the frontend rather than the backend. 
The usage requires that the user has a NodeJs 14.0 or higher installed.

You can use NVM (Node Version Manager) to make sure that you have a compatible version installed. The LTS version should work but if you experience problems, then you may need to check BokehJs for it's latest compatible version and use that one.
```shell
> nvm install --lts
> nvm use --lts
```


## Nice To Have

Some things did not make it into Coda yet. 

*   **Legends**\
    Eventually add a legend for the color and marker factor maps. 
    The rows in the spreadsheet view could also be colored accordingly.
*   **HistogramView**\
    Add classical boxplot features like whiskers, min max and outlier views. 
*   **ImageView and Thumbnails**\
    Add a column to the data frame with the paths to images for each sample. 
    The ImageView then shows a grid with the thumbnails of the current selection and the thumbnails may also be attached to the hover tool.
*   **3D Point Clouds**\
    This could help to identify clusters in 3D, not relying only on 2D scatter plots.
*   **Isomorphic 2D Graph Layout**\ 
    Use the Buddy-Angles to create an isomorphic as possible 2D graph layout of the Codal framework.


## Rationale

This section contains some design rationales and also why I decided against some features.

*   **Reloading and Delayed Update Process**\
    Handling the reloading in a stable manner is a bit tricky. 
    The multi-stage process looks roughly like this:
    *   The data provider detects a change and notifies the CoDA application.
    *   An automatic reload is triggered or the user is notified.
    *   CoDA sets the *is_reloading* flag to *True*.
    *   The data provider reloads the data.
    *   The views and helpers updated additional render information and store them in the data frames *df* and *df_edges.
    *   The Bokeh column data sources are updated with the content in the *df* and *df_edges* data frames.
    *   The views update the plots to account for the new data if needed.
    *   The reload is done and Coda sets the *is_reloading* flag to *False*.


## References

*   The CoDA preprint. \
    https://doi.org/10.48550/arXiv.2406.18236
*   The CoDA repository. \
    https://github.com/zibamira/CTcoral_CoDA
*   The A2W dataset, published on Panges. \
    https://doi.pangaea.de/10.1594/PANGAEA.969578 \
    https://doi.pangaea.de/10.1594/PANGAEA.969464


## License

This project is released under the [MIT License](LICENSE).