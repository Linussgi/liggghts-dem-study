from parameter_sweep import Parameter, Study
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(script_dir, "..", "study-templates")
output_dir = os.path.join(script_dir, "..", "sweep-output")


MAX_AMP = 0.00764829669

n_particles = Parameter("num_particles", "resodyn.sim", [30000, 150000], 5)
friction = Parameter("fric_pp", "particles.sim", [0, 2], 5)
amplitude = Parameter("amp", "resodyn.sim", [0, MAX_AMP], 5)

my_study = Study([n_particles, friction, amplitude], templates_dir)
my_study.generate_studies(output_dir)