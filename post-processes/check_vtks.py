import os
import pyvista as pv
import csv

def check_vtk_files_in_post_folder(post_folder_path, invalid_files_list):
    valid_files = 0
    invalid_files = 0

    # Iterate through all files in the post folder
    for filename in os.listdir(post_folder_path):
        # Looking for "particles_\d+" vtk files
        if filename.startswith("particles_") and filename[10].isdigit():
            file_path = os.path.join(post_folder_path, filename)
            
            try:
                mesh = pv.read(file_path)
                
                # Check the mesh contains particles
                if mesh.n_points > 1000:
                    valid_files += 1
                else:
                    invalid_files += 1
                    invalid_files_list.append({
                        'Simulation Folder': os.path.basename(post_folder_path),
                        'File Name': filename
                    })
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                invalid_files += 1
                invalid_files_list.append({
                    'Simulation Folder': os.path.basename(post_folder_path),
                    'File Name': filename
                })

    return valid_files, invalid_files

def process_simulation_folders(root_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # CSV for the statistics of the VTK files
    output_csv = os.path.join(output_folder, "vtk_file_validation_results.csv")
    
    # CSV for storing invalid VTK filenames
    invalid_csv = os.path.join(output_folder, "invalid_vtk_files.csv")
    
    with open(output_csv, mode="w", newline="") as csvfile:
        fieldnames = ["Simulation Name", "Valid VTKs", "Invalid VTKs", "Valid Fraction", "Total VTKs"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # List to store invalid VTK files 
        invalid_files_list = []

        # Go through through each simulation folder in the root folder
        for simulation_folder in os.listdir(root_folder):
            simulation_path = os.path.join(root_folder, simulation_folder)

            if os.path.isdir(simulation_path):
                print(f"Processing simulation: {simulation_folder}")

                post_folder_path = os.path.join(simulation_path, "post")


                if os.path.isdir(post_folder_path):
                    # Get valid and invalid VTK counts for this simulation's post folder
                    valid_count, invalid_count = check_vtk_files_in_post_folder(post_folder_path, invalid_files_list)

                    total_count = valid_count + invalid_count
                    valid_fraction = valid_count / total_count if total_count > 0 else 0

                    writer.writerow({
                        "Simulation Name": simulation_folder,
                        "Valid VTKs": valid_count,
                        "Invalid VTKs": invalid_count,
                        "Valid Fraction": valid_fraction,
                        "Total VTKs": total_count
                    })
                else:
                    print(f"Warning: 'post' folder not found in {simulation_folder}")

        # Write the invalid files data to the second CSV
        if invalid_files_list:
            with open(invalid_csv, mode="w", newline="") as invalid_file:
                invalid_fieldnames = ["Simulation Folder", "File Name"]
                invalid_writer = csv.DictWriter(invalid_file, fieldnames=invalid_fieldnames)
                invalid_writer.writeheader()
                invalid_writer.writerows(invalid_files_list)

    print(f"Results saved to {output_csv} and {invalid_csv}")


root_folder = f"../sweep_output/" 
output_folder = "check_vtks_output" 

print("Started vtk check...")
process_simulation_folders(root_folder, output_folder)
