import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Define the rotation matrix (desk rotated 45 degrees around the Z-axis)
rotation_matrix = np.array([
    [0.707, 0.707, 0],
    [-0.707, 0.707, 0],
    [0, 0, 1]
])

# Initial position of the desk's origin in the room's global coordinates
desk_origin = np.array([10, 5, 0])

# Basis vectors of the desk's local coordinate system (in global coordinates)
x_desk_global = rotation_matrix @ np.array([1, 0, 0])
y_desk_global = rotation_matrix @ np.array([0, 1, 0])
z_desk_global = rotation_matrix @ np.array([0, 0, 1])

# Translation in the desk's local coordinates (e.g., move 2 units along local X, 3 along local Y)
translation_local = np.array([2, 3, 0])

# Translate the vector into global coordinates
translation_global = rotation_matrix @ translation_local

# New position of the desk's origin after translation
new_desk_origin = desk_origin + translation_global

# Plotting the original and new positions of the desk
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot the original desk position
ax.quiver(desk_origin[0], desk_origin[1], desk_origin[2], x_desk_global[0], x_desk_global[1], x_desk_global[2], color='r', label='X_desk (original)')
ax.quiver(desk_origin[0], desk_origin[1], desk_origin[2], y_desk_global[0], y_desk_global[1], y_desk_global[2], color='g', label='Y_desk (original)')
ax.quiver(desk_origin[0], desk_origin[1], desk_origin[2], z_desk_global[0], z_desk_global[1], z_desk_global[2], color='b', label='Z_desk (original)')

# Plot the new desk position
ax.quiver(new_desk_origin[0], new_desk_origin[1], new_desk_origin[2], x_desk_global[0], x_desk_global[1], x_desk_global[2], color='r', linestyle='--', label='X_desk (translated)')
ax.quiver(new_desk_origin[0], new_desk_origin[1], new_desk_origin[2], y_desk_global[0], y_desk_global[1], y_desk_global[2], color='g', linestyle='--', label='Y_desk (translated)')
ax.quiver(new_desk_origin[0], new_desk_origin[1], new_desk_origin[2], z_desk_global[0], z_desk_global[1], z_desk_global[2], color='b', linestyle='--', label='Z_desk (translated)')

# Label the origins with smaller text size
ax.text(desk_origin[0], desk_origin[1], desk_origin[2], f'Origin (initial)\n{desk_origin}', color='k', fontsize=8, ha='right')
ax.text(new_desk_origin[0], new_desk_origin[1], new_desk_origin[2], f'Origin (translated)\n{new_desk_origin}', color='k', fontsize=8, ha='right')

# Plot settings
ax.set_xlim([0, 15])
ax.set_ylim([0, 15])
ax.set_zlim([0, 5])
ax.set_xlabel('X (Room)')
ax.set_ylabel('Y (Room)')
ax.set_zlabel('Z (Room)')
ax.legend()

# Show the plot
plt.show()
