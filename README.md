# Cora - The Coral Explorer

~ [Input](#input)
~ [Visualization](#visualization)
~ [ToDo](#todo)
~ [Usage](#usage)
~ [Rationale](#rationale)
~

This Python package implements *Cora - The Coral Explorer* application. An interactive link-and-brush tool with a real-time interface to Amira. It allows a fast visualization and exploration of cold-water corals, but doubles down as a general non-application specific explorative analysis tool.

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

*   TableView\
    This view shows the raw data columns.
*   FlowerView\
    This view shows a flower (start) plot of 
    the aggregated selected data.


*   Scatter Plots\
    The user can select and configure a scatter plot with all features.
*   Dimensionality Reduction\
    A UMAP dimension reduction is perfomed when one of the inputs change
    and updated automatic in the frontend. The features are visualized in 
    a scatter plot. 

## Usage

Please take a look at the [examples/](./examples) folder for examples. You should already be familiar with NumPy.

## ToDo

*   HistogramView
    *   Create a dedicated histogram view for a single
        data frame.
*   ScatterView
    *   Create a dedicated view for the scatter plot 
        of 2 columns.

*   SimpleML
    *   Create a view for the UMap settings
    *   Create a view for the PCA settings
*   MapView
    *   Create a MapView which shows the "longitute" and "latitude" columns.

*   CLIDataProvider
    *   Create a general purpose data provider.
    *   The provider takes a list of paths via the command line interface and watches their creation and modification.
    *   The provider also takes the path to a numpy image containing the row indices. This mask is used to create a selection mask.
    *   

# Tuesday

*   Create the UMAP UI and widget.
    *   Feature selection
    *   UMap parameters
*   Visualize the location in a map view.
    *   Add a location column to the vertex data provider
    *   Add a map view.

# Wednesday

*   Use new attributes in the application class "image_vertices" and "image_edges"
    *   I don't know why I wrote this todo point. Probably for thumbnails
        of the vertices and edges

# Thursday

*   AMIRA data provider
    *   new class "data provider" which sets up the project
    *   encapsulates the reload button, has a dirty flag
    *   selection mask synchronization
    *   create a new tool for seeking the instance in Amira, take a look at https://docs.bokeh.org/en/2.4.1/docs/user_guide/extensions_gallery/tool.html

# Future

*   Clean up UI
    *   clean up controls in code
    *   add group filters/prefix filters in select menus

*   Compute the orientation of the edges and a likelihood for the correct
    orientation. This code could be part of the Amira data provider.
*   Compute more graph attributes in the Amira data provider, e.g.
    the connected component.
*   Compute the budding angle. In the most simple case, consider the medial
    lines of the corals to be straight lines. Compute the inplane angle
    between both lines as budding angle. A more sophisticated approach 
    would use the tangential vectors of the quadratic polyp medial line
    approximation below.
*   Approximate the medial line by a quadratic curve (parabola) fitted
    to the point cloud of a polyp. The second order coefficient (curvature)
    and the first order coefficient (straightness) may be useful features.
*   Center Line Tree
    Radius Lifting Tree Paper
*   Using the Buddy-Angles, try to create an isomorphic as possible 2D
    embedding of the coral framework.
    
*   Other applications
    *   Jürgen could eventually use the PCA features for the element origin analysis
        he showed me a year ago. Let's ask him.

## Nice To Have

*   Legends\
    Eventually add a legend for the color and marker factor maps. The rows in the 
    spreadsheet view could also be colored accordingly.
*   HistogramView\
    Add classical boxplot features like whiskers, min max
    and outlier views. Draw continous, kernel-density estimator based curves.

## Rationale

This section contains some design rationales and also why I decided against some features.

*   **Filter Widgets**\
    Filter widgets usually work with range widgets or select menu. The range based filtering can be done with the BoxSelection tool and the select menu similarly in the scatter plot view. So it was not worth the trouble adding these widgets when they are not as easy to use. After all, the mouse tools allow for a better interactive approach.