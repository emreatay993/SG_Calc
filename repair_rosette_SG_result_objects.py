# region Import necessary libraries
import re
import context_menu
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Get the list of unsuppressed SG_Grid_Body  and their names in the tree
list_of_obj_of_all_bodies = DataModel.Project.GetChildren(DataModelObjectCategory.Body,True)
list_of_obj_of_SG_grid_bodies = [
    list_of_obj_of_all_bodies[i]
    for i in range(len(list_of_obj_of_all_bodies))
    if list_of_obj_of_all_bodies[i].Name.Contains("SG_Grid_Body_")
    and list_of_obj_of_all_bodies[i].Thickness == Quantity('0 [m]')
    and list_of_obj_of_all_bodies[i].ObjectState == ObjectState.FullyDefined]
    
list_of_names_of_SG_grid_bodies = [
    list_of_obj_of_all_bodies[i].Name
    for i in range(len(list_of_obj_of_all_bodies))
    if list_of_obj_of_all_bodies[i].Name.Contains("SG_Grid_Body_")
    and list_of_obj_of_all_bodies[i].Thickness == Quantity('0 [m]')
    and list_of_obj_of_all_bodies[i].ObjectState == ObjectState.FullyDefined]
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Get the list of unsuppressed SG_Grid_Body objects in the tree and remove them
list_of_obj_of_all_elastic_strains = DataModel.Project.GetChildren(DataModelObjectCategory.NormalElasticStrain,True)
list_of_obj_of_SG_grid_strains = [
    list_of_obj_of_all_elastic_strains[i]
    for i in range(len(list_of_obj_of_all_elastic_strains))
    if list_of_obj_of_all_elastic_strains[i].Name.Contains("StrainX_SG")]

DataModel.Tree.Activate(list_of_obj_of_SG_grid_strains)
if len(list_of_obj_of_SG_grid_strains) > 0:
    context_menu.DoEditDelete(ExtAPI)
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Get the list of StrainX_SG objects to be added
list_of_names_of_SG_grid_strains = [name.replace("SG_Grid_Body", "StrainX_SG") for name in list_of_names_of_SG_grid_bodies]
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Add StrainX_SG results that are missing in the tree
for i in range(len(list_of_names_of_SG_grid_strains)):
    # region Add strain results for each SG grid for postprocessing time vs strain data in each channel
    body_selection_of_missing_SG_strainx_results = \
    ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    body_selection_of_missing_SG_strainx_results.Ids = [
        DataModel.GetObjectsByName(list_of_names_of_SG_grid_bodies[i])[0].GetGeoBody().Id]
    
    normal_strain_x_SG_grid = sol_selected_environment.AddNormalElasticStrain()
    normal_strain_x_SG_grid.Location = body_selection_of_missing_SG_strainx_results
    normal_strain_x_SG_grid.CoordinateSystem = None  # Results will be in Solution CS
    normal_strain_x_SG_grid.CalculateTimeHistory = True
    normal_strain_x_SG_grid.Name = list_of_names_of_SG_grid_strains[i]
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Group StrainX_SG objects together
list_of_obj_of_tree_group_of_StrainX_SG = [
    DataModel.GetObjectsByName(sol_selected_environment.Children[i].Name)[0]
    for i in range(len(sol_selected_environment.Children))
    if sol_selected_environment.Children[i].Name.Contains("StrainX_SG")
    and sol_selected_environment.Children[i].DataModelObjectCategory == DataModelObjectCategory.TreeGroupingFolder]

# Ungroup the folder and its contents
[list_of_obj_of_tree_group_of_StrainX_SG[i].Ungroup() 
for i in range(len(list_of_obj_of_tree_group_of_StrainX_SG))]

# Get the updated list of all StrainX_SG objects in the tree
list_of_obj_of_all_elastic_strains = DataModel.Project.GetChildren(DataModelObjectCategory.NormalElasticStrain,True)
list_of_obj_of_SG_grid_strains = [
    list_of_obj_of_all_elastic_strains[i]
    for i in range(len(list_of_obj_of_all_elastic_strains))
    if list_of_obj_of_all_elastic_strains[i].Name.Contains("StrainX_SG")]

# Group existing StrainX_SG objects back again
ExtAPI.DataModel.Tree.Activate(list_of_obj_of_SG_grid_strains)
context_menu.DoCreateGroupingFolderInTree(ExtAPI)
DataModel.GetObjectsByName("New Folder")[0].Name = "StrainX_SG"
# endregion