import pandas as pd
import numpy as np
import re
from openpyxl import load_workbook

E = 200e9
v = 0.3

# ... [Other functions remain unchanged] ...

# Load the CSV file into a pandas DataFrame
file_path = 'SG_sample_out_data_sg_filtered_v2_long_test.csv'
data = pd.read_csv(file_path)
print("Selected test data:", file_path)

# Load the CSV file containing the rosette angles
angles_file_path = 'rosette_angles.csv'
rosette_angles_df = pd.read_csv(angles_file_path)
print("Selected rosette angles data:", angles_file_path)

time = data['Time']
strain_gauge_data = data.iloc[:, 1:].filter(regex='SG')

# Extract unique strain gauge numbers from the column headers
sg_numbers = sorted(set(int(re.search(r'SG(\d+)_', col).group(1)) for col in strain_gauge_data.columns if re.search(r'SG(\d+)_', col)))

for sg_number in sg_numbers:
    sg_cols = [col for col in strain_gauge_data.columns if f'SG{sg_number}_' in col]

    # Ensure there are three columns per strain gauge
    if len(sg_cols) == 3:
        rosette_row = rosette_angles_df[rosette_angles_df['SG'] == sg_number]
        if not rosette_row.empty:
            current_angles = rosette_row.iloc[0, 1:].values
            strains = strain_gauge_data[sg_cols].values
            global_strains = np.array([transform_strains_to_global(*strain, current_angles) for strain in strains])
            principal_strains = np.array([calculate_principal_strains(strain[0], strain[1], strain[2]) for strain in global_strains])
            principal_stresses = np.array([calculate_principal_stresses(strain, E, v) for strain in principal_strains])
            principal_strain_orientation = np.array([calculate_principal_strain_orientation(strain[0], strain[1], strain[2]) for strain in global_strains])
            biaxiality_ratios = calculate_biaxiality_ratio(principal_stresses[:, 0], principal_stresses[:, 1])
            von_mises_stresses = np.array([calculate_von_mises_stress(*stress) for stress in principal_stresses])
            for i, strain_type in enumerate(['epsilon_x [με]', 'epsilon_y [με]', 'gamma_xy [με]']):
                strain_gauge_data[f'SG{sg_number}_{strain_type}'] = global_strains[:, i]
            strain_gauge_data[f'SG{sg_number}_sigma_1 [MPa]'], strain_gauge_data[f'SG{sg_number}_sigma_2 [MPa]'] = principal_stresses.T
            strain_gauge_data[f'SG{sg_number}_theta_p [°]'] = principal_strain_orientation
            strain_gauge_data[f'SG{sg_number}_Biaxiality_Ratio'] = biaxiality_ratios
            strain_gauge_data[f'SG{sg_number}_von_Mises [MPa]'] = von_mises_stresses
        else:
            print(f'Angles for Rosette {sg_number} not found in angles file.')
    else:
        print(f'Unexpected number of columns for Rosette {sg_number}.')

strain_gauge_data.insert(0, 'Time', time)
excel_file_path = "strain_gauge_data_results.xlsx"
strain_gauge_data.to_excel(excel_file_path, index=False)
wb = load_workbook(excel_file_path)
ws = wb.active
columns_to_hide = [col for col in ws.columns if col[0].value is not None and 'von_Mises' not in col[0].value and col[0].value != 'Time']
for column in columns_to_hide:
    ws.column_dimensions[column[0].column_letter].hidden = True
wb.save(excel_file_path)

strain_gauge_data
