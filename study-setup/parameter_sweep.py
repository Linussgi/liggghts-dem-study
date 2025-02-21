from typing import List, Tuple
import warnings

import numpy as np
import os
import itertools
import shutil
from jinja2 import Environment, FileSystemLoader, Template


class Parameter:
    def __init__(self, name: str, filename: str, bounds: List[float], samples: int):
        self.name = name
        self.filename = filename
        self.samples = samples
        self.values = np.linspace(bounds[0], bounds[1], samples, endpoint=True)


class Study:
    def __init__(self, parameters: List[Parameter], templates_location: str):
        self.parameters = parameters
        self.templates_location = templates_location

        dynamic_files = []
        for param in self.parameters:
            if param.filename not in dynamic_files:
                dynamic_files.append(param.filename)
        
        self.dynamic_files = dynamic_files

    
    def get_jinja_templates(self, templates_dir: str) -> List[Tuple[Template, List[str]]]:
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
    

    def generate_phase_space(self) -> List[List[float]]:
        parameter_values = [param.values for param in self.parameters]
        phase_space_combinations = list(itertools.product(*parameter_values))
        
        return np.array(phase_space_combinations)
    

    def get_param_names(self) -> List[str]:
        return [param.name for param in self.parameters]
        

    def generate_studies(self, output_dir: str) -> None:
        param_combinations = self.generate_phase_space()
        param_names = self.get_param_names()

        for combination in param_combinations:
            study_name = ", ".join([f"{name}: {value}" for name, value in zip(param_names, combination)])

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

            if "run.sh" not in all_files:
                warnings.warn(f"No `run.sh` file detected in {self.templates_location}. It is possible the run file has a different name, or that it is not present.")

            for file in all_files:
                if file.endswith(".stl"):
                    break
            else:
                warnings.warn("No `.stl` file detected") 
            
            for file in static_files:
                source_path = os.path.join(self.templates_location, file)
                destination_path = os.path.join(study_path, file)

                shutil.copy(source_path, destination_path)  