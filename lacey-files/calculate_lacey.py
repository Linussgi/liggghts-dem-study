from ProcessSimulation import ProcessSimulationTimestep, split_particles

import numpy as np
import os
import glob
from natsort import natsorted
from tqdm import tqdm
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

def parallel_run(simulation_state,
                 save_file,
                 split_dicts, 
                 split_columns, 
                 mesh_resolution, 
                 mesh_constant, 
                 start_rotation, 
                 timestep, 
                 min_particles, 
                 mesh_column):
    
    x_split_dict, y_split_dict, z_split_dict, r_split_dict = split_dicts
    x_split_column, y_split_column, z_split_column, r_split_column = split_columns

    simulation_state.append_particle_column(x_split_dict, x_split_column)
    simulation_state.append_particle_column(y_split_dict, y_split_column)
    simulation_state.append_particle_column(z_split_dict, z_split_column)
    simulation_state.append_particle_column(r_split_dict, r_split_column)

    in_mesh_particles, out_of_mesh_particles = simulation_state.mesh_particles(
                                                mesh_resolution, mesh_constant, start_rotation
                                                )

    x_lacey, dropped_particles = simulation_state.lacey_mixing(
                                                    x_split_column, mesh_column, min_particles
                                                    )

    y_lacey, dropped_particles = simulation_state.lacey_mixing(
                                                    y_split_column, mesh_column, min_particles
                                                    )

    z_lacey, dropped_particles = simulation_state.lacey_mixing(
                                                    z_split_column, mesh_column, min_particles
                                                    )

    r_lacey, dropped_particles = simulation_state.lacey_mixing(
                                                    r_split_column, mesh_column, min_particles
                                                    )

    time = simulation_state.time(timestep)

    simulation_state.save_particles(save_file)

    return [time, x_lacey, y_lacey, z_lacey, r_lacey, 
                in_mesh_particles, out_of_mesh_particles, dropped_particles]

# Example name
study_format = "num_particles: *, fric_pp: *, amp: *" 

def main():
    # Mesh parameters
    cylinder_prefix = "mesh_"
    split_dimensions = ["x", "y", "z", "r"]
    mesh_resolution = [8,6,20]
    mesh_constant = "volume"
    mesh_column = "mesh"

    # Simulation parameters
    timestep = 1e-5
    dumpstep = 0.1
    settled_time = 2

    # Lacey mixing parameters
    min_particles = 10
    start_rotation = 0

    # Check for exit codes CSV
    exit_codes_file = "non_zero_exit_codes.csv"
    excluded_studies = set()
    
    if os.path.exists(exit_codes_file):
        try:
            exit_codes_df = pd.read_csv(exit_codes_file)
            excluded_studies = set(exit_codes_df['study_name'].tolist())
            print(f"Found {len(excluded_studies)} studies to exclude from processing")
        except Exception as e:
            print(f"Error reading exit codes file: {e}")
    else:
        print("No exit code CSV file found. Proceeding as normal")

    # study directories 
    glob_study = os.path.join("../sweep_output", study_format)
    all_studies = natsorted([f for f in glob.glob(glob_study)])
    
    # Filter out and print excluded studies
    study_list = []
    for study in all_studies:
        study_name = os.path.basename(study)
        if study_name in excluded_studies:
            print(f"Ignored study {study_name} due to nonzero exit code")
        else:
            study_list.append(study)

    print(f"Current working directory: {os.getcwd()}")
    print(f"Looking for pattern: {glob_study}")
    print(f"Found {len(all_studies)} total studies")
    print(f"Processing {len(study_list)} studies after excluding {len(all_studies) - len(study_list)} studies")
    if study_list:
        print("First 5 studies to process:", study_list[:5])
    
    # Check if any studies were found
    if not study_list:
        print("No valid studies found to process")
        return
    
    df = None  # Initialize df 

    # Loop over all studies
    for i, study in enumerate(tqdm(study_list)):
        study_name = os.path.basename(study)

        # Get all particle files in the study
        glob_input = os.path.join(study, "post", "particles_*")
        files = natsorted([f for f in glob.glob(glob_input) if "boundingBox" not in f])
        
        if not files:
            print(f"No particle files found in study: {study_name}")
            continue

        # Get the split particles for the settled file
        settled_file = files[round(settled_time/dumpstep)]

        split_dicts = []
        split_columns = []
        for split_dimension in split_dimensions:
            split_dict, split_column = split_particles(settled_file, split_dimension)
            split_dicts.append(split_dict)
            split_columns.append(split_column)

        simulation_state_list = []
        for particles_file in files:
            # Retrieve corresponding cylinder file for each particle file
            file_name_id = os.path.basename(particles_file).split("_")[1].split(".")[0]
            cylinder_name = cylinder_prefix + file_name_id +'.vtk'
            cylinder_file = os.path.join(os.path.dirname(particles_file), cylinder_name)

            # Generate simulation state object for each file in the study
            simulation_state = ProcessSimulationTimestep(particles_file, cylinder_file)
            simulation_state_list.append(simulation_state)

        # Save files list for each study
        save_file_list = [os.path.join(os.path.dirname(sim.filepath),
                            f"lacey_{sim.filename}") 
                            for sim in simulation_state_list]

        # Arguments for parallel run
        args = ((*inputs, split_dicts, split_columns, mesh_resolution, 
                mesh_constant, start_rotation, timestep, min_particles, 
                mesh_column) for inputs in zip(simulation_state_list, save_file_list))

        # Run parallel processing of files in study
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = executor.map(parallel_run, *zip(*args))
            results = np.array([f for f in futures])

        # Save parallel run results to dataframe
        study_df = pd.DataFrame(results, columns = ["time", 
                                                    f"{study_name} x lacey",
                                                    f"{study_name} y lacey",
                                                    f"{study_name} z lacey",
                                                    f"{study_name} r lacey",  
                                                    f"{study_name} in mesh particles",  
                                                    f"{study_name} out of mesh particles",
                                                    f"{study_name} dropped particles"])

        # Merge all study dataframes
        if df is None:
            df = study_df
        else:
            df = df.merge(study_df, how="outer", on="time")

    # Check if we have any data before saving
    if df is not None:
        df.to_csv("lacey_results.csv")
        print("Successfully saved results to lacey_results.csv")
    else:
        print("No data was processed, no CSV file was created")

if __name__ == "__main__":
    main()