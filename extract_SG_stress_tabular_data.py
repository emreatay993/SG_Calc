import csv
import time

# Record the start time
start_time = time.time()

# list_of_obj_of_SG_stress_probes

list_of_obj_of_all_result_probes = DataModel.Project.GetChildren(DataModelObjectCategory.ResultProbe,True)
list_of_obj_of_SG_stress_probes = [
    list_of_obj_of_all_result_probes[i]
    for i in range(len(list_of_obj_of_all_result_probes))
    if list_of_obj_of_all_result_probes[i].Name.Contains("StressVM_SG_Probe")]


# Helper function to check if a string can be converted to float
def is_float(element):
    try:
        float(element)
        return True
    except ValueError:
        return False

time_data = []
list_of_stress_data = []
headers_stress = []
headers_microstrain = []

for m in range(len(list_of_obj_of_SG_stress_probes)):

    DataModel.GetObjectsByName(list_of_obj_of_SG_stress_probes[m].Name)[0].Activate()
    Pane = ExtAPI.UserInterface.GetPane(MechanicalPanelEnum.TabularData)
    Con = Pane.ControlUnknown

    flat_list = []
    for C in range(1, Con.ColumnsCount + 1):
        for R in range(1, Con.RowsCount + 1):
            Text = Con.cell(R, C).Text
            if Text is not None:
                flat_list.append(Text)

    numeric_list = [float(item) for item in flat_list if is_float(item)]

    num_elements_per_column = len(numeric_list) // 3
    columns = [numeric_list[i * num_elements_per_column: (i + 1) * num_elements_per_column] for i in range(3)]

    # Extract and modify the names of each column data
    headers_stress.append(list_of_obj_of_SG_stress_probes[m].Name.Substring(9) + "_FEA [MPa]")
    headers_microstrain.append(list_of_obj_of_SG_stress_probes[m].Name.Substring(9) + "_FEA [MPa]")

    # Assuming each inner list of columns is a separate column of data
    list_of_stress_data.append(columns[2])


time_data.append(columns[1])
time_data = time_data[0]

# Add Time as the first header in both headers lists
headers_stress.insert(0, "Time")

# Transpose the list of lists so each inner list becomes a column
transposed_data = list(map(list, zip(*list_of_stress_data)))

# Define the path where you want to save the CSV file for stress data
csv_file_name = "SG_FEA_stressVM_data.csv"
file_path = project_path + "/" + csv_file_name  # Assuming project_path is defined elsewhere

# Write the stress data to a CSV file
with open(file_path, 'wb') as file:
    writer = csv.writer(file)
    writer.writerow(headers_stress)  # Write the header row first
    for index, row in enumerate(transposed_data):
        writer.writerow([time_data[index]] + row)  # Prepend time data to each row

print("SG FEA StressVM CSV file created at: " + file_path)

# Record the end time
end_time = time.time()

# Calculate the execution time
execution_time = end_time - start_time

# Print the execution time in seconds
print("Execution time: {:.2f} seconds".format(execution_time))