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

## Usage

Please take a look at the [examples/](./examples) folder for examples. You should already be familiar with NumPy.