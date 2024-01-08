code_string = """
def after_post(this, solution):

    import pandas as pd
    import plotly.express as px
    
    # Load the data
    file_name = 'SG_FEA_microstrain_data.csv'
    file_path = project_path + "/" + file_name
    data = pd.read_csv(file_path)
    data_long = data.melt(id_vars='Time', var_name='Gauge Channel', value_name='με')
    
    fig = px.line(data_long, x='Time', y='με', color='Strain Gauge', title='SG Channels (FEA)')
    
    fig.show()
    
    pass
"""
def check_for_duplicate_codes_in_tree():
    list_of_obj_of_all_python_codes = DataModel.Project.GetChildren(
                                      DataModelObjectCategory.PythonCodeEventBased,True)
    list_of_obj_of_plot_SG_channels_FEA = [
        list_of_obj_of_all_python_codes[i]
        for i in range(len(list_of_obj_of_all_python_codes))
        if list_of_obj_of_all_python_codes[i].Name.Contains("Plot SG Channels (FEA)")]

    if len(list_of_obj_of_plot_SG_channels_FEA)>=1:
        
        # Define the message, caption, and buttons for the message box
        message = r"""There is already at least one duplicate Python Code object in the tree. Please delete it first to be able to run this button again."""
        caption = "Warning"
        buttons = MessageBoxButtons.OK
        icon = MessageBoxIcon.Warning
        # Show the message box
        result = MessageBox.Show(message, caption, buttons, icon)
        
    if len(list_of_obj_of_plot_SG_channels_FEA)==0:
        plot_SG_FEA = sol_selected_environment.AddPythonCodeEventBased()
        plot_SG_FEA.Name = "Plot SG Channels (FEA)"
        plot_SG_FEA.TargetCallback=PythonCodeTargetCallback.OnAfterPost
        plot_SG_FEA.PropertyByName("EngineType").InternalValue = 1  # Set as CPython
        plot_SG_FEA.Text = code_string
        plot_SG_FEA.ScriptExecutionScope = '__python_code_666__'
        plot_SG_FEA.Connect()

check_for_duplicate_codes_in_tree()