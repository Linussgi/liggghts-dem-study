import warnings

import numpy as np
import os
import itertools
import shutil
from jinja2 import Environment, FileSystemLoader, Template
from natsort import natsorted
import glob


class Parameter:
    """
    A class to store the attributes of a parameter.

    Attributes:
        name (str): This name should be the same as the parameter's placeholder name in within the template files. 
        filename (str): This is the name of the template file that this parameter appears in.
        values: (List[float]): The values this parameter can take withiin the parameter space.
    """
    def __init__(self, name: str, filename: str, values: list[float]):
        self.name = name
        self.filename = filename
        self.values = values
        self.samples = len(values)


class Study:
    """
    A class to define and generate a N-dimensional parameter case study specified by the user.

    Attributes:
        parameters (List[Parameter]): A list of Parameter objects representing the parameters the user wishes to vary.
        templates_location (str): The directory containing template files each simulation requires.
        dynamic_files (List[str]): A list of filename within the template location that contain one or more of the parameters being varied.
    """
    def __init__(self, parameters: list[Parameter], templates_location: str):
        self.parameters = parameters
        self.templates_location = templates_location

        dynamic_files = []
        for param in self.parameters:
            if param.filename not in dynamic_files:
                dynamic_files.append(param.filename)
        
        self.dynamic_files = dynamic_files

    
    def get_jinja_templates(self, templates_dir: str) -> list[tuple[Template, list[str]]]:
        """
        Loads Jinja2 templates and associates them with their corresponding parameters.

        Args:
            templates_dir (str): The directory containing the template files.

        Returns:
            List[Tuple[Template, List[str]]]: A list of tuples where each tuple contains:
                - A Jinja2 Template object.
                - A list of parameter names used in the template.
        """
        env = Environment(loader=FileSystemLoader(templates_dir))
        
        template_data = []
        for file in self.dynamic_files:
            template = env.get_template(file)

            param_names = []
            for param in self.parameters:
                if param.filename == file:
                    param_names.append(param.name)

            template_data.append((template, param_names))

        return template_data
    

    def generate_phase_space(self) -> np.ndarray:
        """
        Generates all combinations of parameter values.

        Returns:
            np.ndarray: An array where each row represents a unique combination of parameter values within the parameter space.
        """
        parameter_values = [param.values for param in self.parameters]
        phase_space_combinations = list(itertools.product(*parameter_values))
        
        return np.array(phase_space_combinations)
    

    def get_param_names(self) -> list[str]:
        """
        Returns a list of the names of all parameters being studied.
        """
        return [param.name for param in self.parameters]
        

    def generate_studies(self, output_dir: str) -> None:
        """
        Generates a study directory for each combination of parameters . Within each directory, all files within `study-templates` are copied in.
            - Files named in `self.dyanmic_files` will have their templates rendered with a unique parameter combination when copied in.
            - Files named in the `static_files` local variable will be copied in as they are with no modification.

        Args:
            output_dir (str): The directory where all generated studies will be saved.
        """
        param_combinations = self.generate_phase_space()
        param_names = self.get_param_names()

        iteration = 0
        for combination in param_combinations:
            study_name = "-".join([f"{name}_{value}" for name, value in zip(param_names, combination)])

            study_path = os.path.join(output_dir, study_name)

            os.makedirs(study_path, exist_ok=True)

            for template, params_in_template in self.get_jinja_templates(self.templates_location):
                param_dict = {name: value for name, value in zip(param_names, combination)}
                filtered_params = {name: param_dict[name] for name in params_in_template}

                rendered_content = template.render(**filtered_params)

                template_filename = os.path.basename(template.name) 
                output_file_path = os.path.join(study_path, template_filename)

                with open(output_file_path, "w") as sim_file:
                    sim_file.write(rendered_content)

            all_files = os.listdir(self.templates_location)
            static_files = [file for file in all_files if file not in self.dynamic_files]

            # Check for bash script to run workflow 
            if "run.sh" not in all_files:
                warnings.warn(f"No `run.sh` file found in {self.templates_location}. It is possible the run file has a different name, or is not present.")

            # Check that geometry was present in template files
            for file in all_files:
                if file.endswith(".stl"):
                    break
            else:
                warnings.warn(f"No `.stl` file found in {self.templates_location}. It is possible the stl file has a different name, or is not present.") 
            
            for file in static_files:
                source_path = os.path.join(self.templates_location, file)
                destination_path = os.path.join(study_path, file)

                shutil.copy(source_path, destination_path)

            iteration += 1

        print(f"Created {iteration} studies in {output_dir}")  

    
    def slurm_launch(self, output_dir):
        """
        Submits SLURM jobs for each study directory (each simulation) in the output directory.

        Args:
            output_dir (str): The directory containing study folders.

        Returns:
            None
        """
        study_format = self.get_study_format()

        run_folders = natsorted(glob.glob(os.path.join(output_dir, study_format))) 
        for index, run_folder in enumerate(run_folders):
            launch_file = os.path.join(run_folder, "run.sh")
            cmd = f"sbatch --output={run_folder}/slurm-%j.out {launch_file} {run_folder}"

            run_folder_name = os.path.basename(run_folder)  
            parent_folder_name = os.path.basename(os.path.dirname(run_folder))  
            print(f"Submitting job for {parent_folder_name}/{run_folder_name}: Job {index + 1}")

            os.system(cmd)  # Submit job


    def get_study_format(self):
        """
        Generates a format string to match study directories.

        Returns:
            str: The study format string.
        """
        param_names = self.get_param_names()

        return "-".join([f"{name}_*" for name in param_names])
