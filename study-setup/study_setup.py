from study_classes import Parameter, Study
import os
import numpy as np

# Define paths 
templates_dir = "./study-templates"
output_dir = "./sweep-output"

# ---------------------------------------------------------------------

# Define parameter ranges
particle_values = np.linspace(30000, 150000, 5, endpoint=True)
friction_values = np.linspace(0, 2, 5, endpoint=True)
amplitude_values = np.linspace(0, 0.01, 5, endpoint=True)

# Ceate Parameter objects
n_particles = Parameter("numParticles", "resodyn.sim", particle_values)
friction = Parameter("fricPp", "particles.sim", friction_values)
amplitude = Parameter("amp", "resodyn.sim", amplitude_values)

# Create Study object and generate study directories
my_study = Study([n_particles, friction, amplitude], templates_dir)
my_study.generate_studies(output_dir)

# Submit simulations as SLURM jobs 
# my_study.slurm_launch(output_dir)

print(f"Study name format is: {my_study.get_study_format()}")