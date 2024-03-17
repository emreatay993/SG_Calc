# Strain Sensitivity Matrix

'''
Generates the strain sensitivity matrix [A]. 
To get the values of the matrix a unit load study should be specified, where each unit load case should be specified in a different analysis environment and also should contain "Unit_Load_Study_LC_" in their name in the Mechanical tree. 
The program gets each analysis environment from top to bottom, assuming that they go from the first unit load case (LC1) to the last unit load case (LC{end}). 
The columns of the matrix specifies are those load cases. 
Within each analysis environment, the results from each normal strain result objects with "StrainX_SG" in their names and that are NOT suppressed, are extracted. 
Each extracted value is the average value of that strain gauge result. 
The columns of sensitivity matrix correspond to the response of each strain gauge for each unit load case. 
Therefore the rows in each column correspond to sensitivity of each strain gage to that unit load case.
'''


import csv
import os

list_of_obj_of_all_analysis_environments = DataModel.Project.GetChildren(DataModelObjectCategory.Analysis,True)

# Filter all analysis environments that contains "Unit_Load_Study_LC_" in their names
list_of_obj_of_analysis_environments_of_unit_load_studies = [
    list_of_obj_of_all_analysis_environments[i]
    for i in range(len(list_of_obj_of_all_analysis_environments))
    if list_of_obj_of_all_analysis_environments[i].Name.Contains("Unit_Load_Study_LC_")]

''' 
From environments with "Unit_Load_Study_LC_" in their names,
- Get the objects with SG_ in their names if:
    - Their result type is normal elastic strain contours and
    - They are NOT suppressed
    - They have "StrainX_SG" in their names
'''
list_of_obj_of_SG_results_of_unit_load_studies = [
    [list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Average.Value
     for k in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children))
     if list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Name.Contains("SG_")
     and list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].DataModelObjectCategory == DataModelObjectCategory.NormalElasticStrain
     and list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Suppressed == False]
    for i in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies))
]

# Check if all inner lists have the same length
list_lengths = [len(inner) for inner in list_of_obj_of_SG_results_of_unit_load_studies]
if min(list_lengths) != max(list_lengths):
    raise ValueError("The number of extracted values are different for each load case. Please check whether all the analyses have the same number of SGs with name StrainX_SG and they are all evaluated and their results are correct.")

# Write to CSV file in a specified project path
csv_file_path = os.path.join(project_path, 'strain_sensitivity_matrix.csv')
with open(csv_file_path, 'wb') as csvfile:
    writer = csv.writer(csvfile)
    
    # Use zip(*list_of_obj_of_SG_results_of_unit_load_studies) to transpose the list of lists
    for row in zip(*list_of_obj_of_SG_results_of_unit_load_studies):
        writer.writerow(row)

# Show the generated strain sensitivity matrix [A]
message = r"""
The script for generating the strain sensitivity matrix [A] is run successfully.
Please verify the contents of the generated CSV file in the specified project path by the "Project Folder" button.
"""
msg = Ansys.Mechanical.Application.Message(message, MessageSeverityType.Info)
ExtAPI.Application.Messages.Add(msg)

# Open the CSV file with the default application
if os.name == 'nt':  # For Windows
    os.startfile(csv_file_path)