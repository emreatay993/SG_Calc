import csv
import time

# Record the start time
start_time = time.time()

list_of_obj_of_all_elastic_strains = DataModel.Project.GetChildren(DataModelObjectCategory.NormalElasticStrain,True)
list_of_obj_of_SG_grid_strains = [
    obj for obj in list_of_obj_of_all_elastic_strains if obj.Name.Contains("StrainX_SG")
]

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

for m in range(len(list_of_obj_of_SG_grid_strains)):

    DataModel.GetObjectsByName(list_of_obj_of_SG_grid_strains[m].Name)[0].Activate()
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

    # Extract and modify the names of each column data
    headers_strain.append(list_of_obj_of_SG_grid_strains[m].Name.Substring(8) + "_FEA [eps]")
    headers_microstrain.append(list_of_obj_of_SG_grid_strains[m].Name.Substring(8) + "_FEA [mu_eps]")

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
file_path = project_path + "/" + csv_file_name  # Assuming project_path is defined elsewhere

# Write the original strain data to a CSV file
with open(file_path, 'wb') as file:
    writer = csv.writer(file)
    writer.writerow(headers_strain)  # Write the header row first
    for index, row in enumerate(transposed_data):
        writer.writerow([time_data[index]] + row)  # Prepend time data to each row

print("SG FEA strain CSV file created at: " + file_path)

# Now create a new list of lists with the values multiplied by 1e6 for microstrain
SG_FEA_microstrain_data = [[value * 1e6 for value in row] for row in transposed_data]

# Define the path for the microstrain CSV file
SG_FEA_microstrain_csv_file_name = "SG_FEA_microstrain_data.csv"
SG_FEA_microstrain_file_path = project_path + "/" + SG_FEA_microstrain_csv_file_name  

# Write the microstrain data to a CSV file
with open(SG_FEA_microstrain_file_path, 'wb') as file:
    writer = csv.writer(file)
    writer.writerow(headers_microstrain)  # Write the header row first
    for index, row in enumerate(SG_FEA_microstrain_data):
        writer.writerow([time_data[index]] + row)  # Prepend time data to each row

print("SG FEA microstrain CSV file created at: " + SG_FEA_microstrain_file_path)


# Record the end time
end_time = time.time()

# Calculate the execution time
execution_time = end_time - start_time

# Print the execution time in seconds
print("Execution time: {:.2f} seconds".format(execution_time))
