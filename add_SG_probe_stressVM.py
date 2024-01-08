# Extracting reference points and their IDs for strain gauges.
i=0

list_of_obj_of_CS_SG_ref_points = [
    Model.CoordinateSystems.Children[i]
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ref")
]
list_of_IDs_of_CS_SG_ref_points = [
    Model.CoordinateSystems.Children[i].ObjectId
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ref")
]

j = 1
for i in range(len(list_of_IDs_of_CS_SG_ref_points)):
    
    obj_of_SG_stress_SG_probe = sol_selected_environment.AddStressProbe()
    obj_of_SG_stress_SG_probe.LocationMethod = LocationDefinitionMethod.CoordinateSystem
    obj_of_SG_stress_SG_probe.CoordinateSystemSelection = list_of_obj_of_CS_SG_ref_points[i]
    obj_of_SG_stress_SG_probe.Orientation = list_of_obj_of_CS_SG_ref_points[i]
    obj_of_SG_stress_SG_probe.Name = "StressVM_SG_Probe_" + str(i + 1) + "_" + str(j)
    
    j += 1
    
    
def group_SG_objects_created():
    
    list_of_obj_of_all_result_probes = DataModel.Project.GetChildren(DataModelObjectCategory.ResultProbe,True)
    list_of_obj_of_SG_stress_probes = [
        list_of_obj_of_all_result_probes[i]
        for i in range(len(list_of_obj_of_all_result_probes))
        if list_of_obj_of_all_result_probes[i].Name.Contains("StressVM_SG_Probe")]
    
    # Group the strain result objects of SG grids
    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_SG_stress_probes)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "StressVM_SG_Probe"
    
group_SG_objects_created()
    