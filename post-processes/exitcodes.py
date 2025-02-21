import os
import glob
import csv
from collections import defaultdict

DL = 75 # Output delimiter length (for visual ease of reading output)

base_dir = "../sweep_output"
output_dir = "../lacey-files" # csv output
study_format = "fric_*_cor_*" 

os.makedirs(output_dir, exist_ok=True)

# Store exit code frequencies, vtk file counts and non zero exit codes
exit_code_counts = defaultdict(int)
vtk_file_counts = defaultdict(int)
non_zero_exit_codes = []

# Iterate through all studies
for folder in glob.glob(os.path.join(base_dir, study_format)):

    if os.path.isdir(folder):

        # Look for slurm.stats files
        slurm_files = glob.glob(os.path.join(folder, "slurm-*.stats"))
    
        for slurm_file in slurm_files:
            if os.path.isfile(slurm_file):
                with open(slurm_file, "r") as f:
                    slurm_content = f.read()

                    # Extract the exit code from the slurm.stats file
                    exit_code = None
                    for line in slurm_content.splitlines():
                        if "| Exitcode" in line:

                            # Exitcode is in the format "| Exitcode 0:0"
                            parts = line.split()
                            if len(parts) > 1:
                                exit_code = parts[2].split(":")[0]  # Get the first part before the colon in exit_code
                            break
                    
                    if exit_code is not None:
                        exit_code_counts[exit_code] += 1
                        
                        # Add to the list if exit code is non-zero
                        if exit_code != "0":
                            study_name = os.path.basename(folder)
                            non_zero_exit_codes.append((study_name, exit_code))

        # Check for post directory to count .vtk files
        post_dir = os.path.join(folder, "post")
        
        if os.path.isdir(post_dir):
            vtk_files = glob.glob(os.path.join(post_dir, "*.vtk"))
            num_vtk_files = len(vtk_files)

            vtk_file_counts[num_vtk_files] += 1


csv_file_path = os.path.join(output_dir, "non_zero_exit_codes.csv")

print("=" * DL)

# Write studies with non-zero exit codes to the CSV file and print some output data
if non_zero_exit_codes:
    with open(csv_file_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["study_name", "exit_code"])  
        writer.writerows(non_zero_exit_codes)

    print(f"{len(non_zero_exit_codes)} studies with non-zero exit codes have been written to '{csv_file_path}'.")
else:
    print("No studies with non-zero exit codes found.")

print("-" * DL)


if exit_code_counts:
    print("Frequency of exit codes per study:")
    for code, count in sorted(exit_code_counts.items()):
        print(f"{count} studies had exit code {code}")
else:
    print("No exit codes found in any slurm-*.stats files.")

print("-" * DL)


if vtk_file_counts:
    print("Frequency of .vtk file counts per study:")
    for num_files, count in sorted(vtk_file_counts.items()):
        print(f"{count} studies had {num_files} vtk files")
else:
    print("No .vtk files found in any 'post' directories.")

print("=" * DL)