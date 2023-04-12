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

*   Scatter Plots\
    The user can select and configure a scatter plot with all features.
*   Dimensionality Reduction\
    A UMAP dimension reduction is perfomed when one of the inputs change
    and updated automatic in the frontend. The features are visualized in 
    a scatter plot. 

## Usage

Please take a look at the [examples/](./examples) folder for examples. You should already be familiar with NumPy.

## ToDo

*   Interactive SPLOM plots
*   UMAP UI
    *   Features selection
*   Use new attributes in the application class "image_vertices" and "image_edges"
*   AMIRA data provider
    *   new class "data provider" which sets up the project
    *   encapsulates the reload button, has a dirty flag
    *   selection mask synchronization
    *   create a new tool for seeking the instance in Amira, take a look at https://docs.bokeh.org/en/2.4.1/docs/user_guide/extensions_gallery/tool.html
*   Clean up UI
    *   clean up controls in code
    *   add group filters/prefix filters in select menus
*   Add a column for the location of the coral specimen. This may also be part
    of the Amira data provider. 
*   Visualize the location in a map view.

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
    
*   Other applications
    *   Jürgen could eventually use the PCA features for the element origin analysis
        he showed me a year ago. Let's ask him.

## Rationale

This section contains some design rationales and also why I decided against some features.

*   **Filter Widgets**\
    Filter widgets usually work with range widgets or select menu. The range based filtering can be done with the BoxSelection tool and the select menu similarly in the scatter plot view. So it was not worth the trouble adding these widgets when they are not as easy to use. After all, the mouse tools allow for a better interactive approach.