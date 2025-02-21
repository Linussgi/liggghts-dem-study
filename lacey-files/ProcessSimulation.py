import pyvista as pv
import os
import numpy as np
import warnings

class ProcessSimulationTimestep():

    def __init__(self, particles_file, cylinder_file):

        self.filepath = particles_file
        self.filename = os.path.basename(particles_file)
        self.file_name_id = int(os.path.basename(particles_file).split("_")[1].split(".")[0])
        self.particles_file = pv.read(particles_file)
        self.cylinder_file = pv.read(cylinder_file)


    def time(self, timestep):

        # convert the step number to a time value
        self.time = round(timestep*self.file_name_id, 8)

        return self.time
        

    def append_particle_column(self, id_dict, column_name):

        # Check if the particles file has an id column and if it has points
        # If it does, append the new column to the particles file
        if 'id' in self.particles_file.point_data.keys() and self.particles_file.n_points != 0:

            new_column = np.zeros(len(self.particles_file["id"]))
            new_column[:] = np.nan

            # Loop through the id dictionary and assign the new column values
            for key, value in id_dict.items():
                new_column[self.particles_file["id"] == key] = value
                
            self.particles_file[column_name] = new_column

        else:

            # If the particles file does not have an id column or has no points
            # raise a warning and return the object
            warnings.warn("No id column found in particles file or no points in particles file"
                          " therefore column not appended")

        return self.particles_file

    def mesh_particles(self, mesh_resolution, mesh_constant="volume", start_rotation=0):
        
        # Check if the particles file has points
        if self.particles_file.n_points == 0:
            warnings.warn("cannot mesh empty particles file")
            return [np.nan, np.nan]

        # Perform checks on the input variables
        if len(mesh_resolution) != 3:
            raise ValueError("mesh_resolution must be a list of 3 integers")

        if not all([isinstance(i, int) for i in mesh_resolution]):
            raise ValueError("mesh_resolution must be a list of 3 integers")

        if not isinstance(start_rotation, (int, float)):
            raise ValueError("start_rotation must be an integer or float")

        # specify lacey mesh resolution
        ang_mesh = mesh_resolution[0]
        rad_mesh = mesh_resolution[1]
        z_mesh = mesh_resolution[2]

        self.mesh_resolution = mesh_resolution

        # determine the radius of the cylinder mesh
        x_radii = abs(self.cylinder_file.bounds[1] - self.cylinder_file.bounds[0])/2
        y_radii = abs(self.cylinder_file.bounds[3] - self.cylinder_file.bounds[2])/2
        
        # calculate the radial increments of the lacey meshing depending on a chosen constant
        if mesh_constant == "radius":
            radial_mesh_boundaries = np.linspace(0, max(x_radii, y_radii), rad_mesh + 1)

        elif mesh_constant == "volume":
            max_radii_squared = max(x_radii, y_radii)**2
            radial_mesh_boundaries = np.sqrt(
                np.linspace(0, max_radii_squared, rad_mesh + 1)
                )

        else:
            raise("Invalid mesh constant")

        # calculate linearly spaced z mesh boundaries
        z_mesh_boundaries = np.linspace(self.cylinder_file.bounds[4], self.cylinder_file.bounds[5], z_mesh + 1)

        # calculate linearly spaced angular mesh boundaries
        angular_mesh_boundaries = np.linspace(0, 2*np.pi, ang_mesh + 1)

        self.angular_mesh_boundaries = angular_mesh_boundaries
        self.radial_mesh_boundaries = radial_mesh_boundaries
        self.z_mesh_boundaries = z_mesh_boundaries

        x_center = self.cylinder_file.center[0]
        y_center = self.cylinder_file.center[1]

        # calculate particle z positions
        particle_z = self.particles_file.points[:,2]

        # calculate particle radial positions
        particle_radii = np.sqrt(
            (self.particles_file.points[:, 0] - x_center)**2
            + (self.particles_file.points[:, 1] - y_center)**2
            )

        # calculate particle angular positions for x rotate by pi/6
        resolved_angular_data = ( np.arctan2(
            (self.particles_file.points[:,1] - y_center),
            (self.particles_file.points[:,0] - x_center)
            ) + np.pi + start_rotation ) % (2*np.pi)

        # Set up an nan list to hold particle mesh regions
        particle_mesh_element = np.zeros(len(self.particles_file.points))
        particle_mesh_element[:] = np.nan

        # set mesh identifier counter
        counter = 0

        # Loop through the lacey mesh elements
        for k in range(len(z_mesh_boundaries) - 1):

            # Particle above lower z boundary
            above_lower_z = particle_z >= z_mesh_boundaries[k]
            # Particle below upper z boundary
            below_upper_z = particle_z < z_mesh_boundaries[k+1]

            for i in range(len(radial_mesh_boundaries) - 1):

                # Particle above lower radial boundary
                above_lower_r = particle_radii >= radial_mesh_boundaries[i]
                # Particle below upper radial boundary
                below_upper_r = particle_radii < radial_mesh_boundaries[i+1]

                for j in range(len(angular_mesh_boundaries) - 1):

                    # Particle above lower angular boundary
                    above_lower_angle = resolved_angular_data >= angular_mesh_boundaries[j]
                    # Particle below upper angular boundary
                    below_upper_angle = resolved_angular_data < angular_mesh_boundaries[j+1]

                    # pyvista_ndarray boolean mask outlining if a point lies within this
                    # given mesh elemnent
                    mesh_element = (
                        (above_lower_z & below_upper_z) &
                        (above_lower_r & below_upper_r) &
                        (above_lower_angle & below_upper_angle)
                    )

                    # Write mesh identifier to particles inside the mesh element
                    particle_mesh_element[mesh_element] = counter

                    counter += 1

        self.particles_file["mesh"] = particle_mesh_element

        out_of_mesh_particles = sum(np.isnan(particle_mesh_element))
        in_mesh_particles = len(particle_mesh_element) - out_of_mesh_particles

        return [in_mesh_particles, out_of_mesh_particles]


    def lacey_mixing(self, split_column, mesh_column, min_particles):
        
        
        if split_column not in self.particles_file.point_data.keys():
            warnings.warn(f"{split_column} not found in particle file, returning NaN")
            return [np.nan, np.nan]

        if len(np.unique(self.particles_file[split_column])) != 2: 
            raise Exception("Lacey can only support 2 particle types")

        class_0_split = (self.particles_file[split_column].astype(int) 
                        ^ np.ones(len(self.particles_file[split_column])).astype(int))

        class_1_split = self.particles_file[split_column].astype(int)

        mesh = self.particles_file[mesh_column]
        mesh_ids = np.unique(mesh)
        mesh_ids = mesh_ids[~np.isnan(mesh_ids)].astype(int)

        mesh_id_booleans = []
        for ids in mesh_ids:
            mesh_boolean_mask = mesh == ids
            mesh_id_booleans.append(mesh_boolean_mask)

        num_particle_class_0_meshed = []
        num_particle_class_1_meshed = []
        total_num_mesh_particle = []

        # Set up an nan list to hold particle concentrations
        particles_concentration = np.zeros(len(self.particles_file.points))
        particles_concentration[:] = np.nan

        # Set up an nan list to hold particle mesh regions
        mesh_elements = np.zeros(len(self.particles_file.points))
        mesh_elements[:] = np.nan


        # Initial number of dropped particles before looping through mesh elements
        dropped_particles = 0
        # Initial number of lacey mesh elements used for lacey mixing
        n_mesh_elements = 0

        # Loop through the lacey mesh elements
        for mesh_element in mesh_id_booleans:

            mesh_particles_class_0 = class_0_split & mesh_element
            mesh_particles_class_1 = class_1_split & mesh_element

            num_particle_class_0 = sum(mesh_particles_class_0)
            num_particle_class_1 = sum(mesh_particles_class_1)
            total_num_particle = num_particle_class_0 + num_particle_class_1

            if total_num_particle >= min_particles:

                # Append number of particles of class 0 and 1 present in the lacey mesh
                # element to the relevent arrays
                num_particle_class_0_meshed.append(num_particle_class_0)
                num_particle_class_1_meshed.append(num_particle_class_1)
                total_num_mesh_particle.append(total_num_particle)

                # Assign the concentration value of the mesh element to all particles that
                # reside in the mesh element. Used for concentration visualisation
                particles_concentration[mesh_element] = (
                    num_particle_class_1
                        / (
                            num_particle_class_0
                            + num_particle_class_1
                        )
                    )

                # All particles present in the mesh
                n_mesh_elements += 1

            else:
                dropped_particles += total_num_particle

        # Append particle concentration and mesh elements to the self.particles_file
        self.particles_file[f"{split_column}_concentration"] = particles_concentration
        
        # Convert lists to numpy arrays
        num_particle_class_1_meshed = np.asarray(num_particle_class_1_meshed)
        num_particle_class_0_meshed = np.asarray(num_particle_class_0_meshed)
        total_num_mesh_particle = np.asarray(total_num_mesh_particle)

        # Calculate lacey mixing index
        if n_mesh_elements < 2:
            warnings.warn(
                (f"Fewer than 2 non-empty lacey mesh for file {self.filename}"
                "setting Lacey to NaN, consider refining lacey mesh"),
                UserWarning,
            )
            lacey = np.nan
        else:

            bulk_concentration = np.sum(num_particle_class_1_meshed) / np.sum(total_num_mesh_particle)

            concentrations = (
                num_particle_class_1_meshed
                / (
                    num_particle_class_0_meshed
                    + num_particle_class_1_meshed
                )
            )

            variance = np.sum(total_num_mesh_particle
                / np.sum(total_num_mesh_particle)
                * (
                    (concentrations - bulk_concentration) ** 2
                )
            )

            unmixed_variance = bulk_concentration * (1 - bulk_concentration)

            mixed_variance = unmixed_variance / (total_num_mesh_particle).mean()

            lacey = (variance - unmixed_variance) / (mixed_variance - unmixed_variance)


        return [lacey, dropped_particles]


    def save_particles(self, save_file):
        self.particles_file.save(save_file)


def split_particles(settled_file, split_dimension):

    settled_data = pv.read(settled_file)
    split_column = f"{split_dimension}_class"

    if split_dimension == "x":
        split_class  = np.asarray(
            settled_data.points[:, 0] >= np.median(settled_data.points[:, 0])).astype(int)

    elif split_dimension == "y":
        split_class  = np.asarray(
            settled_data.points[:, 1] >= np.median(settled_data.points[:, 1])).astype(int)

    elif split_dimension == "z":
        split_class  = np.asarray(
            settled_data.points[:, 2] >= np.median(settled_data.points[:, 2])).astype(int)

    elif split_dimension == "r":
        median_r2 = np.median(settled_data.points[:, 0]**2 + settled_data.points[:, 1]**2)
        settled_r2 = settled_data.points[:, 0]**2 + settled_data.points[:, 1]**2
        split_class  = np.asarray(settled_r2 >= median_r2).astype(int)

    elif split_dimension == "radius":

        radii = np.unique(settled_data["radius"])
        split_class = np.zeros(settled_data.n_points)
        split_class[:] = np.nan
        for i, radius in enumerate(radii):
            boolean_mask = [settled_data["radius"] == radius]
            split_class[boolean_mask] = i

    else:
        raise ValueError(f"{split_dimension} is not a recognised split dimension")

    split_dict = dict(map(lambda i,j : (i,j), settled_data["id"], split_class))

    return split_dict, split_column