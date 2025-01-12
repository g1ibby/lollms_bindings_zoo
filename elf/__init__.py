######
# Project       : lollms
# File          : binding.py
# Author        : ParisNeo with the help of the community
# Underlying 
# engine author : Google 
# license       : Apache 2.0
# Description   : 
# This is an interface class for lollms bindings.

# This binding is a wrapper to open ai's api

######
from pathlib import Path
from typing import Callable
from lollms.config import BaseConfig, TypedConfig, ConfigTemplate, InstallOption
from lollms.paths import LollmsPaths
from lollms.binding import LLMBinding, LOLLMSConfig
from lollms.helpers import ASCIIColors
from lollms.types import MSG_TYPE
from lollms.com import LoLLMsCom
import subprocess
import yaml
import re
import json
import requests
from datetime import datetime
from typing import List, Union

__author__ = "parisneo"
__github__ = "https://github.com/ParisNeo/lollms_bindings_zoo"
__copyright__ = "Copyright 2023, "
__license__ = "Apache 2.0"

binding_name = "Elf"
binding_folder_name = ""
elf_completion_formats={
    "instruct":"/v1/completions",
    "chat":"/v1/chat/completions",
}

def get_binding_cfg(lollms_paths:LollmsPaths, binding_name):
    cfg_file_path = lollms_paths.personal_configuration_path/"bindings"/f"{binding_name}"/"config.yaml"
    return LOLLMSConfig(cfg_file_path,lollms_paths)

def get_model_info(url):
    url = f'{url}/v1/models'
    headers = {'accept': 'application/json'}
    response = requests.get(url, headers=headers)
    data = response.json()
    model_info = []

    for model in data['data']:
        model_name = model['id']
        owned_by = model['owned_by']
        created_timestamp = model['created']
        created_datetime = datetime.utcfromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        model_info.append({'model_name': model_name, 'owned_by': owned_by, 'created_datetime': created_datetime})

    return model_info
class Elf(LLMBinding):
    
    def __init__(self, 
                config: LOLLMSConfig, 
                lollms_paths: LollmsPaths = None, 
                installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY,
                lollmsCom=None) -> None:
        """
        Initialize the Binding.

        Args:
            config (LOLLMSConfig): The configuration object for LOLLMS.
            lollms_paths (LollmsPaths, optional): The paths object for LOLLMS. Defaults to LollmsPaths().
            installation_option (InstallOption, optional): The installation option for LOLLMS. Defaults to InstallOption.INSTALL_IF_NECESSARY.
        """
        if lollms_paths is None:
            lollms_paths = LollmsPaths()
        # Initialization code goes here


        binding_config = TypedConfig(
            ConfigTemplate([
                {"name":"address","type":"str","value":"http://127.0.0.1:5000","help":"The server address"},
                {"name":"completion_format","type":"str","value":"instruct","options":["instruct","chat"], "help":"The format supported by the server"},
                {"name":"ctx_size","type":"int","value":4090, "min":512, "help":"The current context size (it depends on the model you are using). Make sure the context size if correct or you may encounter bad outputs."},
                {"name":"server_key","type":"str","value":"", "help":"The API key to connect to the server."},
            ]),
            BaseConfig(config={
            })
        )
        super().__init__(
                            Path(__file__).parent, 
                            lollms_paths, 
                            config, 
                            binding_config, 
                            installation_option,
                            supported_file_extensions=[''],
                            lollmsCom=lollmsCom
                        )
        self.config.ctx_size=self.binding_config.config.ctx_size

    def settings_updated(self):
        self.config.ctx_size = self.binding_config.config.ctx_size        
        
    def build_model(self):
        return self

    def install(self):
        super().install()
        ASCIIColors.success("Installed successfully")
        ASCIIColors.error("----------------------")
        ASCIIColors.error("Attention please")
        ASCIIColors.error("----------------------")
        ASCIIColors.error("The google bard binding uses the Google Bard API which is a paid service. Please create an account on the google cloud website then generate a key and provide it in the configuration file.")
    
    def tokenize(self, text: Union[str, List[str]]) -> List[str]:
        """Tokenizes a text string

        Args:
            text (str): The text to tokenize

        Returns:
            A list of tokens
        """
        if isinstance(text, str):
            return text.split()
        else:
            return text

    def detokenize(self, tokens: List[str]) -> str:
        """Detokenizes a list of tokens

        Args:
            tokens (List[str]): The tokens to detokenize

        Returns:
            A string
        """
        return " ".join(tokens)
    
    def generate(self, 
                 prompt: str,                  
                 n_predict: int = 128,
                 callback: Callable[[str], None] = bool,
                 verbose: bool = False,
                 **gpt_params) -> str:
        """Generates text out of a prompt

        Args:
            prompt (str): The prompt to use for generation
            n_predict (int, optional): Number of tokens to predict. Defaults to 128.
            callback (Callable[[str], None], optional): A callback function that is called everytime a new text element is generated. Defaults to None.
            verbose (bool, optional): If true, the code will spit many informations about the generation process. Defaults to False.
        """

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.binding_config.server_key}',
        }
        default_params = {
            'temperature': 0.7,
            'top_k': 50,
            'top_p': 0.96,
            'repeat_penalty': 1.3
        }
        gpt_params = {**default_params, **gpt_params}

        if self.binding_config.completion_format=="instruct":
            data = {
                'model':self.config.model_name,
                'prompt': prompt,
                "stream":True,
                "temperature": float(gpt_params["temperature"]),
                "max_tokens": n_predict
            }
        else:
            data = {
                'model':self.config.model_name,
                'messages': [{
                    'role': "",
                    'content': prompt
                }],
                "stream":True,
                "temperature": float(gpt_params["temperature"]),
                "max_tokens": n_predict
            }

        
        url = f'{self.binding_config.address}{elf_completion_formats[self.binding_config.completion_format]}'

        response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)

        text = ""
        for line in response.iter_lines(): 
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                try:
                    json_data = json.loads(decoded[5:].strip())
                    if self.binding_config.completion_format=="chat":
                        chunk = json_data["choices"][0]["delta"]["content"]
                    else:
                        chunk = json_data["choices"][0]["text"]
                    ## Process the JSON data here
                    text +=chunk
                    if callback:
                        if not callback(chunk, MSG_TYPE.MSG_TYPE_CHUNK):
                            break
                except:
                    break
            else:
                if decoded.startswith("{"):
                    json_data = json.loads(decoded)
                    if json_data["object"]=="error":
                        self.error(json_data["message"])
                        break
                else:
                    text +=decoded
                    if callback:
                        if not callback(decoded, MSG_TYPE.MSG_TYPE_CHUNK):
                            break
        return text

    
    def list_models(self):
        """Lists the models for this binding
        """
        model_names = get_model_info(f'{self.binding_config.address}')
        entries=[]
        for model in model_names:
            entries.append(model["model_name"])
        return entries
                
    def get_available_models(self, app:LoLLMsCom=None):
        # Create the file path relative to the child class's directory
        model_names = get_model_info(f'{self.binding_config.address}')
        entries=[]
        for model in model_names:
            entry={
                "category": "generic",
                "datasets": "unknown",
                "icon": '/bindings/elf/logo.png',
                "last_commit_time": "2023-09-17 17:21:17+00:00",
                "license": "unknown",
                "model_creator": model["owned_by"],
                "model_creator_link": "https://lollms.com/",
                "name": model["model_name"],
                "quantizer": None,
                "rank": "1.0",
                "type": "api",
                "variants":[
                    {
                        "name":model,
                        "size":0
                    }
                ]
            }
            entries.append(entry)
        """
        binding_path = Path(__file__).parent
        file_path = binding_path/"models.yaml"

        with open(file_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
        
        """
        
        return entries