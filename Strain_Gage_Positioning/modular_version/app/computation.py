# File: app/computation.py

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


def load_data(input_filename):
    """Reads the input file and returns nodes, coords, and strain tensors."""
    df = pd.read_csv(input_filename, sep='\s+', skiprows=1, header=None)
    if df.shape[1] < 8:
        raise ValueError("Input file must have at least 8 columns: Node, X, Y, Z, Exx, Eyy, Ezz, Exy...")

    nodes = df.iloc[:, 0].astype(int).values
    coords = df.iloc[:, 1:4].values
    conversion_factor = 1e6  # Convert from strain to microstrain

    # Determine the number of measurements based on columns available
    num_measurements = (df.shape[1] - 4) // 4
    if num_measurements == 0:
        raise ValueError("No strain measurement columns found in the input file.")

    strain_tensors = {}
    for i in range(num_measurements):
        base_col_idx = 4 + 4 * i
        # Ensure that the required columns exist for this measurement
        if base_col_idx + 3 >= df.shape[1]:
            print(f"Warning: Incomplete strain tensor columns for measurement set {i + 1}. Skipping.")
            continue

        exx = df.iloc[:, base_col_idx].values * conversion_factor
        eyy = df.iloc[:, base_col_idx + 1].values * conversion_factor
        exy = df.iloc[:, base_col_idx + 3].values * conversion_factor  # 4th component of tensor is Exy
        strain_tensors[i] = np.column_stack((exx, eyy, exy))

    return nodes, coords, strain_tensors


def compute_normal_strains(strain_data, angles):
    """
    Compute the normal strain for each node at specified angles.

    Args:
        strain_data (np.ndarray): Array of shape (n_nodes, 3) with columns [exx, eyy, exy].
        angles (list or np.ndarray): Angles in degrees to compute strain for.

    Returns:
        np.ndarray: Array of shape (n_nodes, n_angles) with normal strains.
    """
    angles_rad = np.radians(angles)
    cos_t = np.cos(angles_rad)
    sin_t = np.sin(angles_rad)

    # Use broadcasting for efficient computation
    exx = strain_data[:, 0][:, np.newaxis]
    eyy = strain_data[:, 1][:, np.newaxis]
    exy = strain_data[:, 2][:, np.newaxis]

    # Strain transformation equation: ε_n = ε_xx*cos²θ + ε_yy*sin²θ + γ_xy*sinθ*cosθ
    # Note: Engineering shear strain (γ_xy) is 2 * tensor shear strain (ε_xy).
    # The provided data seems to use engineering strain conventions where the tensor is [exx, eyy, ezz, exy],
    # and the transformation uses exy directly. We will assume the input 'exy' is γ_xy.
    normal_strains = exx * cos_t ** 2 + eyy * sin_t ** 2 + exy * sin_t * cos_t

    return normal_strains


def compute_quality_metrics(nodes, coords, strains, angles, quality_mode, uniformity_radius):
    """
    Computes the best strain, best angle, local standard deviation, and a quality metric.

    Args:
        nodes (np.ndarray): Array of node IDs.
        coords (np.ndarray): N-D array of node coordinates.
        strains (np.ndarray): Array of strains, shape (n_nodes, n_angles).
        angles (list or np.ndarray): Angles in degrees.
        quality_mode (str): The formula to use for the quality metric.
        uniformity_radius (float): The search radius for calculating local standard deviation.

    Returns:
        pd.DataFrame: A DataFrame with comprehensive metrics for each node.
    """
    if strains.ndim == 1:
        strains = strains[:, np.newaxis]

    best_idx = np.argmax(np.abs(strains), axis=1)
    best_strains = strains[np.arange(len(strains)), best_idx]
    best_angles = np.array(angles)[best_idx]

    if len(angles) == 1:
        # For modes like von Mises, there is no "best angle"
        best_angles = np.full(len(nodes), np.nan)

    # Use cKDTree for efficient spatial queries
    tree = cKDTree(coords)
    local_std = np.zeros(len(nodes))

    # Query all points at once for better performance
    neighbors_list = tree.query_ball_point(coords, uniformity_radius)

    for i, indices in enumerate(neighbors_list):
        if len(indices) > 1:  # Standard deviation requires at least 2 points
            local_std[i] = np.std(best_strains[indices])

    abs_strain = np.abs(best_strains)

    if quality_mode == "Default: |ε|/(1+σ)":
        quality = abs_strain / (1.0 + local_std)
    elif quality_mode == "Squared: |ε|/(1+σ²)":
        quality = abs_strain / (1.0 + local_std ** 2)
    elif quality_mode == "Exponential: |ε|·exp(–1000σ)":
        quality = abs_strain * np.exp(-1000 * local_std)
    elif quality_mode == "Signal-Noise Ratio: |ε|/(σ+1e-12)":
        # Add a small epsilon to avoid division by zero
        quality = abs_strain / (local_std + 1e-12)
    else:
        raise ValueError(f"Unknown quality_mode: {quality_mode}")

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


def aggregate_quality_metrics(quality_dfs, agg_method):
    """
    Aggregate multiple quality metric DataFrames into a single DataFrame.
    This is used when multiple load cases (measurements) are present.

    Args:
        quality_dfs (list): A list of pandas DataFrames from compute_quality_metrics.
        agg_method (str): The aggregation method ("max" or "average").

    Returns:
        pd.DataFrame: A single DataFrame with the aggregated 'Quality' column.
    """
    if not quality_dfs:
        raise ValueError("No quality dataframes provided for aggregation.")

    # Use the first DataFrame as a template for node/coord info
    agg_df = quality_dfs[0].copy()

    if len(quality_dfs) == 1:
        return agg_df

    quality_matrix = np.stack([df["Quality"].values for df in quality_dfs], axis=1)

    if agg_method.lower() == "max":
        agg_quality = np.max(quality_matrix, axis=1)
    elif agg_method.lower() == "average":
        agg_quality = np.mean(quality_matrix, axis=1)
    else:
        raise ValueError(f"Unknown aggregation method: {agg_method}")

    agg_df["Quality"] = agg_quality
    return agg_df