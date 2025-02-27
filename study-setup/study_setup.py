from parameter_sweep import Parameter, Study
import os
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(script_dir, "..", "study-templates")
output_dir = os.path.join(script_dir, "..", "sweep-output")

particle_values = np.linspace(30000, 150000, 5, endpoint=True)
friction_values = np.linspace(0, 2, 5, endpoint=True)
amplitude_values = np.linspace(0, 0.01, 5, endpoint=True)

n_particles = Parameter("num_particles", "resodyn.sim", particle_values)
friction = Parameter("fric_pp", "particles.sim", friction_values)
amplitude = Parameter("amp", "resodyn.sim", amplitude_values)

my_study = Study([n_particles, friction, amplitude], templates_dir)
my_study.generate_studies(output_dir)