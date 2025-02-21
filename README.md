## LIGGGHTS N-Dimensional Parameter Sweep
The following workflow was created to automate generation and analysis of an N-dimensional parameter sweep over a LIGGGHTS MCC particle simulation. This is to invetsigate the effects of said parameters on particle mixing rate and mixing quality within a cylindrical random acoustic mixer (RAM). 

### Simulation files setup
The user selects a parameter space of N dimensions to investigate. Files that contain the simulation data (such as LIGGGHTS `.sim` files and geometry files) should be stored in `study-templates`. The workflow will create a folder for each study within the parameter space. For example, if the user wishes to invetsigate a 3D parameter space of 4 by 2 by 5, the workflow will create 40 study unique folders, each folder containing simulation files with a different combination of parameters.


1. The user selects the parameters and their values that they want to study. These parameters and their values are defined in `study-setup/study_setup.py`
2. Running this file will create a new folder in the top level directory called `sweep-output`
3. Within `sweep-output`, each study folder is then created
4. The files within `study-templates` are copied into each study folder
5. `jinja2` templating is used to modify the parameters within the template files, if necessary

#### Usage

```python
from parameter_sweep import Parameter, Study
import os

# Defintion of key paths
script_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(script_dir, "..", "study-templates")
output_dir = os.path.join(script_dir, "..", "sweep-output")

# Creation of `Parameter` objects 
n_particles = Parameter("num_particles", "resodyn.sim", [30000, 150000], 5)
friction = Parameter("fric_pp", "particles.sim", [0, 2], 5)
amplitude = Parameter("amp", "resodyn.sim", [0, 0.01], 5)

# Creation of Study object
my_study = Study([n_particles, friction, amplitude], templates_dir)

# Generation of study folders
my_study.generate_studies(output_dir)
```

The Parameter defines each paramater, its name, the file it is located in and its values It takes the following arguments:

- `name: str`: The parameter name as it appears in the template files (this is determined by the user in their simulation template files)
- `filename: str`: The template file where this parameter is used
- `bounds: List[float]`: A list of [min, max] values for the parameter
- `samples: int`: Number of evenly spaced samples to generate between bounds

The Study class manages the parameter sweep and file generation:

- `parameters: List[Parameters]`: The parameter objects defined by the user
- `templates_location: str`: The path to the template folder that contains files that should be copied and potentially modified according to each study
- `Study.generate_studies(outpur_dir: str)`: The method that performs the parameter sweep and creates each study folder within a specified output directory

### `lacey-files` - mixing calculations (credit goes to [@Jack-Grogan](https://github.com/Jack-Grogan))
After LIGGGHTS simulations have been setup and ran, each study folder within `sweep_output` will contain a `post` directory. Within `post` the simulation results are stored in VTK format. The purpose of the following process is to read each study's VTK files, and quantify the level of mixing of MCC particles within the study according to this VTK data.

- `ProcessSimulation.py` defines a class that is used to perform frame by frame analysis of a simulation, by assigning each particles a particle ID and determining its location within the RAM over time. From this data, the level of mixing at any given point in time can be calculated
- `calculate_lacey.py` handles locating and input of simulation VTK files as well as other parameters such as selecting mixing dimensions and saving data to an output CSV

The output of `calculate_lacey.py` is saved to `./lacey_results.csv` with the following headers:

- `index`: the row index
- `time`: the time value at which the data was recorded is shown (in seconds)
- `x lacey`: the Lacey index of all the particles with respect to the x dimension of the geometry 
- `y lacey`: the Lacey index of all the particles with respect to the y dimension of the geometry 
- `z lacey`: the Lacey index of all the particles with respect to the z dimension of the geometry 
- `r lacey`: the Lacey index of all the particles with respect to the r dimension of the geometry 
- `particles out of mesh`: the number of particles inside the mesh 
- `particles out of mesh`: the number of particles that escaped the mesh (usually artefacts of LIGGGHTS calculations)
- `dropped particles`: the number of particles not considered for Lacey index calculation at that specific timestep due to being in a sparsely populated volume of the geometry

Headers 3 to 9 (inclusive) are repeated for all studies in the 2D parameter sweep, with the simulation folder name prepended to each header. So if the parameter sweep was a 5x5 sweep of 2 parameters, `lacey_results.csv` would have 177 columns. 

### Debugging 
The following scripts were created to streamline the debugging process of the LIGGGHTS simulations.

The `exitcodes.py` script: 
- Locates each study within `sweep_output` and checks that LIGGGHTS was able to run each study simulation to completion 
- Does this by checking the exit codes of the LIGGGHTS log files 
- Studies that did not finish with exit code `0` are recorded and saved to a CSV `non_zero_exitcodes.csv` in the `lacey_files` folder. 

The `check_vtks.py` script: 
- Checks each study for invalid VTK files that may have been generated by LIGGGHTS due to calculation artefacts that may arise during simulation. 
- The name of each study and their number of proportion of invalid VTK files are saved to a CSV `check_vtks.csv` within the folder `./check_vtks/`.

### Analysis
The following analysis scripts are used to extract trends and correlations from the data within `lacey_results.csv` created by the Lacey mixing calculations (`calculate_lacey.py`).

#### `lacey_fitting.py` 
Takes the `lacey_results.csv` and fits the Lacey mixing index of each dimension in each study to the following equation using `scipy.optimize`: 

$$y = A(1 - e^{-kt})$$ 

- The parameter $A$ is determined by the maximum value of mixing
- The parameter $k$ is the fitting parameter 
- The Lacey mixing index is fit to the equation using the `time` header as $t$ values 

This means each study has four fitted models associated with it (one fitted model for each dimension x, y, z and r). Results are saved to a CSV `fitted_k_values.csv`. The headers of this CSV are:

- `study name` which is taken from `lacey_results.csv` header name
- `x lacey k` the $k$ value found for Lacey mixing with respect to x
- `y lacey k` the $k$ value found for Lacey mixing with respect to y
- `z lacey k` the $k$ value found for Lacey mixing with respect to z
- `r lacey k` the $k$ value found for Lacey mixing with respect to r

In addition to these 5 columns, there are 8 other columns present that measure the goodness of fit of the each $k$ value: 

- `kx R2`, `ky R2`, `kz R2`, `kr R2` which measure the $R^2$ (correlation strength) of each model with respect to each mixing dimension
- `kx RMSE`, `ky RMSE`, `kz RMSE`, `kr RMSE` which measures the root mean squares error of each model with respect to each mixing dimension

#### `lacey_linegraphs.py`
For quick visualisation purposes. 

- User selects *a single study* (chosen in `lacey_linegraphs.py`) within the parameter space 
- Script plots 2 graphs showing how the Lacey mixing index with respect to each mixing dimension changes with time
- Also plots the fitted four fitted models that correspond to that study on a separate graph

### Requirements

Python 3.12
`numpy 2.2.3`
`pandas 2.2.3`
`jinja2 3.1.5`
`scipy 1.15.1`
`matplotlib 3.10.0`
`pyvista 0.44.2`
