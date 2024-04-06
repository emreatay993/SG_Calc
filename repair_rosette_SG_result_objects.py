# region Import necessary libraries
import re
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Functions for object name/number checking
def extract_grid_and_channel_numbers(names_list, pattern):
    list_of_SG_ref_numbers = []
    list_of_SG_ch_numbers = []
    
    for name in names_list:
        match = re.search(pattern, name)
        if match:
            list_of_SG_ref_numbers.append(int(match.group(1)))
            list_of_SG_ch_numbers.append(int(match.group(2)))
    
    return list_of_SG_ref_numbers, list_of_SG_ch_numbers

#Function to compare lists of reference and channel numbers and find missing elements
def find_missing_elements(ref_numbers_1, ch_numbers_1, ref_numbers_2, ch_numbers_2):
    # Pairing reference and channel numbers as tuples
    paired_list_1 = set(zip(ref_numbers_1, ch_numbers_1))
    paired_list_2 = set(zip(ref_numbers_2, ch_numbers_2))
    
    # Finding missing elements
    missing_in_list_2 = paired_list_1 - paired_list_2  # Elements in list 1 not in list 2
    missing_in_list_1 = paired_list_2 - paired_list_1  # Elements in list 2 not in list 1
    
    return list(missing_in_list_1), list(missing_in_list_2)
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Extract the channel names of SG_Grid_Body reference points that exist in the tree
list_of_obj_of_all_bodies = DataModel.Project.GetChildren(DataModelObjectCategory.Body,True)
list_of_names_of_SG_Grid_Body_of_grids = [
    list_of_obj_of_all_bodies[i].Name
    for i in range(len(list_of_obj_of_all_bodies))
    if list_of_obj_of_all_bodies[i].Name.Contains("SG_Grid_Body")
    and list_of_obj_of_all_bodies[i].DataModelObjectCategory != DataModelObjectCategory.TreeGroupingFolder]
# endregion

# region Extract the channel names of StrainX results that exist in the tree
list_of_obj_of_all_elastic_strains = DataModel.Project.GetChildren(DataModelObjectCategory.NormalElasticStrain,True)
list_of_names_of_SG_grid_strains = [
    list_of_obj_of_all_elastic_strains[i].Name
    for i in range(len(list_of_obj_of_all_elastic_strains))
    if list_of_obj_of_all_elastic_strains[i].Name.Contains("StrainX_SG")]
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Extract the reference and channel number SG_Grid_Body reference points that exist in the tree
pattern_StrainX_SG = r"StrainX_SG(\d+)_(\d+)"
list_of_StrainX_SG_ref_numbers, list_of_StrainX_SG_ch_numbers = extract_grid_and_channel_numbers(list_of_names_of_SG_grid_strains, pattern_StrainX_SG)
# endregion

# region Extract the reference and channel number SG_Grid_Body reference points that exist in the tree
pattern_SG_Grid_Body = r"SG_Grid_Body_(\d+)_(\d+)"
list_of_SG_Grid_Body_ref_numbers, list_of_SG_Grid_Body_numbers = extract_grid_and_channel_numbers(list_of_names_of_SG_Grid_Body_of_grids, pattern_SG_Grid_Body)
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Finding only the missing elements in list_of_StrainX_SG compared to list_of_CS_SG
missing_in_list_of_StrainX = \
find_missing_elements(list_of_StrainX_SG_ref_numbers, 
                      list_of_StrainX_SG_ch_numbers, 
                      list_of_SG_Grid_Body_ref_numbers, 
                      list_of_SG_Grid_Body_numbers)[0]
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Filter elements of list_of_names_of_SG_Grid_Bodies based on missing elements in missing_in_list_of_StrainX
list_of_filtered_names_of_SG_Grid_Bodies = [
    name for name in list_of_names_of_SG_Grid_Body_of_grids
    if any("SG_Grid_Body_{}_{}".format(ref, ch) in name for ref, ch in missing_in_list_of_StrainX)]
# endregion

# region Filter elements of list_of_names_of_SG_Grid_Bodies based on missing elements in missing_in_list_of_StrainX
list_of_filtered_names_of_missing_StrainX_SG = [
    "StrainX_SG{}_{}".format(ref, ch) for ref, ch in missing_in_list_of_StrainX]
# endregion

#-------------------------------------------------------------------------------------------------------------------------------------------------------

# region Add StrainX_SG results that are missing in the tree
for i in range(len(list_of_filtered_names_of_missing_StrainX_SG)):
    # region Add strain results for each SG grid for postprocessing time vs strain data in each channel
    body_selection_of_missing_SG_strainx_results = \
    ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    body_selection_of_missing_SG_strainx_results.Ids = [
        DataModel.GetObjectsByName(list_of_filtered_names_of_SG_Grid_Bodies[i])[0].GetGeoBody().Id]
    
    normal_strain_x_SG_grid = sol_selected_environment.AddNormalElasticStrain()
    normal_strain_x_SG_grid.Location = body_selection_of_missing_SG_strainx_results
    normal_strain_x_SG_grid.CoordinateSystem = None  # Results will be in Solution CS
    normal_strain_x_SG_grid.CalculateTimeHistory = True
    normal_strain_x_SG_grid.Name = list_of_filtered_names_of_missing_StrainX_SG[i]
# endregion


