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

*   Spreadsheet
*   Histogram
*   Scatter
*   SPLOM
*   Graph
*   Map
*   Embedding
*   Flower

# Future

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
*   Update the Amira IPC interface to support ROI selection and use only the watchdog interface and simple spreadsheet/numpy file types.
*   Alternatively to the ROI seeking tool: Create an Amira module which
    adjusts the ROI automatic based on a given label field.

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
    and outlier views. 
*   ImageView and Thumbnails\
    Add a column to the data frame with the paths to images for each sample. The ImageView shows a grid with the thumbnails of the current selection and the thumbnails may also be attached to the hover tool.
*   3D Point Clouds\
    This could help to identify clusters in 3D, not relying only on 2D scatter plots.

## Rationale

This section contains some design rationales and also why I decided against some features.

*   **Filter Widgets**\
    Filter widgets usually work with range widgets or select menu. The range based filtering can be done with the BoxSelection tool and the select menu similarly in the scatter plot view. So it was not worth the trouble adding these widgets when they are not as easy to use. After all, the mouse tools allow for a better interactive approach.