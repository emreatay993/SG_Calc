# region Import necessary libraries
import csv
import time
import os
import re
from System.Windows.Forms import MessageBox,MessageBoxButtons, MessageBoxIcon
# endregion

# ----------------------------------------------------------------------------------------------------------------

# region Define the required functions
# Function to extract reference and channel numbers from a strain name
def extract_numbers(name):
    pattern = r"StrainX_SG(\d+)_(\d+)"
    match = re.search(pattern, name)
    if match:
        return tuple(map(int, match.groups()))
    else:
        return (0, 0)  # Default to (0, 0) if the pattern does not match

# Function to sort the strain names using the extract_numbers function
def sort_strain_names(names):
    sorted_names = sorted(names, key=extract_numbers)
    return sorted_names
# endregion

# ----------------------------------------------------------------------------------------------------------------

# region Get the solution directory and the path
solution_directory_path = sol_selected_environment.WorkingDir
solution_directory_path = solution_directory_path.Replace("\\", "\\\\")
# endregion

# region Get the the names of active StrainX_SG objects in the selected analysis environment
list_of_names_of_SG_grid_strains = [] # Initialize the list

list_of_obj_of_all_elastic_strains = sol_selected_environment.GetChildren(DataModelObjectCategory.NormalElasticStrain,True)
list_of_names_of_SG_grid_strains = [
    obj.Name for obj in list_of_obj_of_all_elastic_strains 
    if obj.Name.Contains("StrainX_SG")
    and obj.ObjectState != ObjectState.Suppressed]

list_of_IDs_of_SG_grid_strains = [
    obj.ObjectId for obj in list_of_obj_of_all_elastic_strains 
    if obj.Name.Contains("StrainX_SG")
    and obj.ObjectState != ObjectState.Suppressed]

# Throw an error if no active StrainX_SG objects are found in the selected analysis environment.
if len(list_of_names_of_SG_grid_strains) == 0:
    MessageBox.Show("There are no active SG strain contours to be extracted within the selected analysis environment.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
# endregion

# ----------------------------------------------------------------------------------------------------------------

# region Make sure that all StrainX_SG objects are and will be evaluated in the ascending order. 
# Pair each ID with its corresponding name
paired_list = list(zip(list_of_IDs_of_SG_grid_strains, list_of_names_of_SG_grid_strains))

# Use your existing sort function on the paired list, sorting by the second element of each pair (the name)
sorted_pairs = sorted(paired_list, key=lambda x: extract_numbers(x[1]))

# Unzip the pairs back into two lists
sorted_IDs, sorted_names = zip(*sorted_pairs)

# Convert tuples back to lists, if necessary
list_of_IDs_of_SG_grid_strains = list(sorted_IDs)
list_of_names_of_SG_grid_strains = list(sorted_names)
# endregion

# ----------------------------------------------------------------------------------------------------------------

# region Convert the tabular data contained in each StrainX_SG result into numerical data
# Helper function to check if a string can be converted to float
def is_float(element):
    try:
        float(element)
        return True
    except ValueError:
        return False

time_data = []
list_of_strain_data = []
headers_strain = []
headers_microstrain = []

for m in range(len(list_of_names_of_SG_grid_strains)):

    DataModel.GetObjectById(list_of_IDs_of_SG_grid_strains[m]).Activate()
    Pane = ExtAPI.UserInterface.GetPane(MechanicalPanelEnum.TabularData)
    Con = Pane.ControlUnknown

    flat_list = []
    for C in range(1, Con.ColumnsCount + 1):
        for R in range(1, Con.RowsCount + 1):
            Text = Con.cell(R, C).Text
            if Text is not None:
                flat_list.append(Text)

    numeric_list = [float(item) for item in flat_list if is_float(item)]

    num_elements_per_column = len(numeric_list) // 5
    columns = [numeric_list[i * num_elements_per_column: (i + 1) * num_elements_per_column] for i in range(5)]

    # Use regular expressions to extract the "SG_x_y" part
    match = re.search(r"(SG\d+_\d+)", list_of_names_of_SG_grid_strains[m])
    if match:
        sg_name = match.group(1)  # Extract the "SG_x_y" part
    else:
        sg_name = "Unknown"  # Default value if the pattern doesn't match

    # Extract and modify the names of each column data
    headers_strain.append(sg_name)
    headers_microstrain.append(sg_name)

    # Assuming each inner list of columns is a separate column of data
    list_of_strain_data.append(columns[4])

time_data.append(columns[1])
time_data = time_data[0]

# Add Time as the first header in both headers lists
headers_strain.insert(0, "Time")
headers_microstrain.insert(0, "Time")

# Transpose the list of lists so each inner list becomes a column
transposed_data = list(map(list, zip(*list_of_strain_data)))

# Define the path where you want to save the CSV file for strain data
csv_file_name = "SG_FEA_strain_data.csv"
file_path = os.path.join(solution_directory_path, csv_file_name)

# Write the original strain data to a CSV file
with open(file_path, 'wb') as file:
    writer = csv.writer(file)
    writer.writerow(headers_strain)  # Write the header row first
    for index, row in enumerate(transposed_data):
        writer.writerow([time_data[index]] + row)  # Prepend time data to each row

print("CSV file for each SG channel (strain in mm/mm) created at: " + file_path)

# Create a new list of lists with the values multiplied by 1e6 for microstrain
SG_FEA_microstrain_data = [[value * 1e6 for value in row] for row in transposed_data]

# Define the path for the microstrain CSV file
SG_FEA_microstrain_csv_file_name = "SG_FEA_microstrain_data.csv"
SG_FEA_microstrain_file_path = os.path.join(solution_directory_path, SG_FEA_microstrain_csv_file_name)  

# Write the microstrain data to a CSV file
with open(SG_FEA_microstrain_file_path, 'wb') as file:
    writer = csv.writer(file)
    writer.writerow(headers_microstrain)  # Write the header row first
    for index, row in enumerate(SG_FEA_microstrain_data):
        writer.writerow([time_data[index]] + row)  # Prepend time data to each row

print("CSV file for each SG channel (microstrain) created at: " + SG_FEA_microstrain_file_path)
# endregion