import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import pyvista as pv
from sklearn.cluster import KMeans


# ================================
# STRAIN AND QUALITY COMPUTATION
# ================================
def compute_normal_strains(strain_data, angles):
    """
    Compute the normal strain for each node and angle.

    ε(θ) = exx*cos²(θ) + eyy*sin²(θ) + 1.0*exy*sin(θ)*cos(θ)
    """
    angles_rad = np.radians(angles)
    cos_t = np.cos(angles_rad)
    sin_t = np.sin(angles_rad)

    exx = strain_data[:, 0][:, np.newaxis]
    eyy = strain_data[:, 1][:, np.newaxis]
    exy = strain_data[:, 2][:, np.newaxis]

    return exx * cos_t ** 2 + eyy * sin_t ** 2 + 1.0 * exy * sin_t * cos_t


def compute_quality_metrics(nodes, coords, strains, angles, quality_mode="snr", uniformity_radius=1.0):
    """
    Computes the best strain, best angle, local standard deviation, and quality metric.
    Returns a DataFrame with the node information.
    """
    # Determine the best strain (and corresponding angle) for each node.
    best_idx = np.argmax(np.abs(strains), axis=1)
    best_strains = strains[np.arange(len(strains)), best_idx]
    best_angles = np.array(angles)[best_idx]
    if len(angles) == 1:
        best_angles = np.full(len(nodes), np.nan)

    # Compute local standard deviation via a KDTree.
    tree = cKDTree(coords)
    local_std = np.zeros(len(nodes))
    for i, point in enumerate(coords):
        indices = tree.query_ball_point(point, uniformity_radius)
        local_std[i] = np.std(best_strains[indices])
    abs_strain = np.abs(best_strains)

    # Compute quality metric.
    if quality_mode == "original":
        quality = abs_strain / (1.0 + local_std)
    elif quality_mode == "squared":
        quality = abs_strain / (1.0 + local_std ** 2)
    elif quality_mode == "exponential":
        quality = abs_strain * np.exp(-1000 * local_std)
    elif quality_mode == "snr":
        epsilon = 1e-12
        quality = abs_strain / (local_std + epsilon)
    else:
        raise ValueError(f"Unknown quality_mode: {quality_mode}")

    # Build a DataFrame with node data.
    return pd.DataFrame({
        'Node': nodes,
        'X': coords[:, 0],
        'Y': coords[:, 1],
        'Z': coords[:, 2],
        'Best_Strain': best_strains,
        'Best_Angle': best_angles,
        'Local_Std': local_std,
        'Quality': quality
    })


# ================================
# CANDIDATE SELECTION FUNCTIONS
# ================================
def greedy_selection(df, min_distance, candidate_count):
    """
    Select candidate points by greedily enforcing a minimum spatial distance.
    """
    selected = []
    selected_coords = []
    # Process the DataFrame sorted by descending quality.
    for _, row in df.iterrows():
        point = np.array([row['X'], row['Y'], row['Z']])
        if not selected_coords or np.all(np.linalg.norm(np.array(selected_coords) - point, axis=1) >= min_distance):
            selected.append(row)
            selected_coords.append(point)
        if len(selected) >= candidate_count:
            break
    return pd.DataFrame(selected)


def select_candidate_points(nodes, coords, strains, angles, candidate_count,
                            min_distance, uniformity_radius, quality_mode="original"):
    """
    Quality-based candidate selection using a greedy algorithm.
    """
    df = compute_quality_metrics(nodes, coords, strains, angles, quality_mode, uniformity_radius)
    df_sorted = df.sort_values(by='Quality', ascending=False)
    return greedy_selection(df_sorted, min_distance, candidate_count)


def select_candidate_points_spatial_quality(nodes, coords, strains, angles, candidate_count,
                                            uniformity_radius, quality_mode="snr"):
    """
    Improved candidate selection that uses KMeans clustering to partition nodes into candidate_count regions.
    The node with the highest quality in each cluster is selected.
    """
    df = compute_quality_metrics(nodes, coords, strains, angles, quality_mode, uniformity_radius)
    kmeans = KMeans(n_clusters=candidate_count, random_state=42).fit(coords)
    labels = kmeans.labels_

    candidate_rows = []
    for cluster in range(candidate_count):
        cluster_df = df[labels == cluster]
        if not cluster_df.empty:
            best_row = cluster_df.loc[cluster_df['Quality'].idxmax()]
            candidate_rows.append(best_row)
    candidate_df = pd.DataFrame(candidate_rows)
    # Optionally, you could run greedy selection here as well.
    return candidate_df.sort_values(by='Quality', ascending=False)


# ================================
# DATA INPUT/OUTPUT FUNCTIONS
# ================================
def load_data(input_filename):
    """
    Reads the input file and returns node, coordinate, and strain information.
    """
    df = pd.read_csv(input_filename, sep='\s+', skiprows=1, header=None)
    if df.shape[1] < 8:
        raise ValueError("Input file does not have the expected coordinate and strain columns.")

    nodes = df.iloc[:, 0].astype(int).values
    coords = df.iloc[:, 1:4].values  # X, Y, Z coordinates.
    exx = df.iloc[:, 4].values
    eyy = df.iloc[:, 5].values
    exy = df.iloc[:, 7].values
    return nodes, coords, exx, eyy, exy


def save_strain_results(output_filename, nodes, coords, strains, header_full):
    """
    Saves the computed strain results to a CSV file.
    """
    output_array = np.column_stack((nodes, coords, strains))
    np.savetxt(output_filename, output_array, delimiter=",", fmt="%.6e",
               header=header_full, comments="")


# ================================
# VISUALIZATION FUNCTIONS
# ================================
def visualize_strain_with_candidates(coords, vm_strains, candidates_df, title):
    """
    Visualizes the full strain field with candidate points annotated by quality.
    """
    cloud = pv.PolyData(coords)
    cloud["Equivalent_Von_Mises_Strain"] = vm_strains
    candidate_coords = candidates_df[['X', 'Y', 'Z']].values
    candidate_points = pv.PolyData(candidate_coords)

    # Create normalized quality labels.
    qualities = candidates_df['Quality'].values
    max_quality = qualities.max() if len(qualities) > 0 else 1
    normalized_qualities = (qualities / max_quality) * 100
    labels = [f"Q: {q:.1f}%" for q in normalized_qualities]

    # Setup the plotter.
    plotter = pv.Plotter()
    plotter.add_mesh(cloud, scalars="Equivalent_Von_Mises_Strain", cmap="jet",
                     point_size=10.0, render_points_as_spheres=True, opacity=1)
    plotter.add_mesh(candidate_points, color="red", point_size=20.0,
                     render_points_as_spheres=True, label="Candidate Points")
    plotter.add_point_labels(candidate_points.points, labels,
                             font_size=14, text_color="black", shape='rounded_rect',
                             shape_color="gray", margin=2, always_visible=True, shadow=True,
                             name="Quality Labels")
    plotter.add_legend()
    plotter.add_axes()
    plotter.show(title=title)


def visualize_kmeans(coords, candidate_count, title="KMeans Clustering of Nodes"):
    """
    Visualizes KMeans clustering of the nodes.
    """
    kmeans = KMeans(n_clusters=candidate_count, random_state=42).fit(coords)
    labels = kmeans.labels_
    cloud = pv.PolyData(coords)
    cloud["Cluster"] = labels
    plotter = pv.Plotter()
    plotter.add_mesh(cloud, scalars="Cluster", cmap="jet", point_size=10.0,
                     render_points_as_spheres=True)
    plotter.add_axes()
    plotter.show(title=title)


# ================================
# MAIN FUNCTION
# ================================
def main():
    # Configuration
    input_filename = "vps_strain4.txt"
    output_filename = "strain_results_interval.csv"
    candidates_filename = "strain_candidate_points.csv"

    measurement_mode = "rosette"  # Options: "rosette" or "uniaxial"
    selection_strategy = "spatial"  # Options: "quality" or "spatial"
    visualize_cluster = True  # Flag to visualize KMeans clustering

    # For uniaxial mode, compute strains at multiple angles; for rosette, a single equivalent strain is computed.
    if measurement_mode == "uniaxial":
        interval = 15
        angles = [0] + list(range(interval, 360, interval))
    else:
        angles = [0]  # Dummy angle for rosette mode

    quality_mode = "snr"  # Options: "original", "squared", "exponential", "snr"
    candidate_count = 10  # Number of candidate nodes to select
    min_distance = 10.0  # Minimum distance for greedy selection
    uniformity_radius = 1.0  # Radius for computing local strain uniformity

    # Load input data.
    nodes, coords, exx, eyy, exy = load_data(input_filename)

    # Compute strains.
    if measurement_mode == "rosette":
        # Compute equivalent von Mises strain.
        vm_strains = np.sqrt(exx ** 2 - exx * eyy + eyy ** 2 + 3 * (exy ** 2))
        strains = vm_strains.reshape(-1, 1)
        header_full = "Node,X,Y,Z,Equivalent_Von_Mises_Strain"
    else:
        strain_data = np.column_stack((exx, eyy, exy))
        strains = compute_normal_strains(strain_data, angles)
        header_full = "Node,X,Y,Z," + ",".join(f"Strain_at_{ang}deg" for ang in angles)

    # Save full strain results.
    save_strain_results(output_filename, nodes, coords, strains, header_full)
    print(f"Full strain results written to: {output_filename}")

    # Candidate selection.
    if selection_strategy == "spatial":
        candidates_df = select_candidate_points_spatial_quality(
            nodes, coords, strains, angles,
            candidate_count=candidate_count,
            uniformity_radius=uniformity_radius,
            quality_mode=quality_mode
        )
    else:
        candidates_df = select_candidate_points(
            nodes, coords, strains, angles,
            candidate_count=candidate_count,
            min_distance=min_distance,
            uniformity_radius=uniformity_radius,
            quality_mode=quality_mode
        )
    candidates_df.to_csv(candidates_filename, index=False)
    print(f"Candidate points written to: {candidates_filename}")

    # Visualization (only for rosette mode in this example).
    if measurement_mode == "rosette":
        visualize_strain_with_candidates(coords, vm_strains, candidates_df,
                                         title="Equivalent von Mises Strain with Candidate Points (Annotated)")

    if visualize_cluster:
        visualize_kmeans(coords, candidate_count)


if __name__ == "__main__":
    main()
