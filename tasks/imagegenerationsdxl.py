import json
import os
from multiprocessing.pool import ThreadPool
from threading import Thread

from backends.nova_server import check_nova_server_status, send_request_to_nova_server
from dvm import DVM
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig

"""
This File contains a Module to transform Text input on NOVA-Server and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
Params: -model         # models: juggernaut, dynavision, colossusProject, newreality, unstable
        -lora          # loras (weights on top of models) voxel, 
"""


class ImageGenerationSDXL(DVMTaskInterface):
    NAME: str = ""
    KIND: int = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "text-to-image"
    COST: int = 50
    PK: str
    DVM = DVM

    def __init__(self, name, dvm_config: DVMConfig, nip89d_tag: str, nip89info: str, admin_config: AdminConfig = None, options=None):
        self.NAME = name
        self.PK = dvm_config.PRIVATE_KEY

        dvm_config.SUPPORTED_TASKS = [self]
        dvm_config.DB = "db/" + self.NAME + ".db"
        dvm_config.NIP89 = self.NIP89_announcement(nip89d_tag, nip89info)
        self.dvm_config = dvm_config
        self.admin_config = admin_config
        self.options = options

    def is_input_supported(self, input_type, input_content):
        if input_type != "text":
            return False
        return True

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        request_form["trainerFilePath"] = 'modules\\stablediffusionxl\\stablediffusionxl.trainer'

        prompt = ""
        negative_prompt = ""
        if self.options.get("default_model"):
            model = self.options['default_model']
        else:
            model = "stabilityai/stable-diffusion-xl-base-1.0"

        ratio_width = "1"
        ratio_height = "1"
        width = ""
        height = ""
        if self.options.get("default_lora"):
            lora = self.options['default_lora']
        else:
            lora = ""
        lora_weight = ""
        strength = ""
        guidance_scale = ""
        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]

            elif tag.as_vec()[0] == 'param':
                print("Param: " + tag.as_vec()[1] + ": " + tag.as_vec()[2])
                if tag.as_vec()[1] == "negative_prompt":
                    negative_prompt = tag.as_vec()[2]
                elif tag.as_vec()[1] == "lora":
                    lora = tag.as_vec()[2]
                elif tag.as_vec()[1] == "lora_weight":
                    lora_weight = tag.as_vec()[2]
                elif tag.as_vec()[1] == "strength":
                    strength = tag.as_vec()[2]
                elif tag.as_vec()[1] == "guidance_scale":
                    guidance_scale = tag.as_vec()[2]
                elif tag.as_vec()[1] == "ratio":
                    if len(tag.as_vec()) > 3:
                        ratio_width = (tag.as_vec()[2])
                        ratio_height = (tag.as_vec()[3])
                    elif len(tag.as_vec()) == 3:
                        split = tag.as_vec()[2].split(":")
                        ratio_width = split[0]
                        ratio_height = split[1]
                    # if size is set it will overwrite ratio.
                elif tag.as_vec()[1] == "size":

                    if len(tag.as_vec()) > 3:
                        width = (tag.as_vec()[2])
                        height = (tag.as_vec()[3])
                    elif len(tag.as_vec()) == 3:
                        split = tag.as_vec()[2].split("x")
                        if len(split) > 1:
                            width = split[0]
                            height = split[1]
                elif tag.as_vec()[1] == "model":
                    model = tag.as_vec()[2]

        io_input = {
            "id": "input_prompt",
            "type": "input",
            "src": "request:text",
            "data": prompt
        }
        io_negative = {
            "id": "negative_prompt",
            "type": "input",
            "src": "request:text",
            "data": negative_prompt
        }
        io_output = {
            "id": "output_image",
            "type": "output",
            "src": "request:image"
        }

        request_form['data'] = json.dumps([io_input, io_negative, io_output])

        options = {
            "model": model,
            "ratio": ratio_width + '-' + ratio_height,
            "width": width,
            "height": height,
            "strength": strength,
            "guidance_scale": guidance_scale,
            "lora": lora,
            "lora_weight": lora_weight
        }
        request_form['options'] = json.dumps(options)

        # old format, deprecated, will remove
        request_form["optStr"] = ('model=' + model + ';ratio=' + str(ratio_width) + '-' + str(ratio_height) + ';size=' +
                                  str(width) + '-' + str(height) + ';strength=' + str(strength) + ';guidance_scale=' +
                                  str(guidance_scale) + ';lora=' + lora + ';lora_weight=' + lora_weight)

        return request_form

    def process(self, request_form):
        try:
            # Call the process route of NOVA-Server with our request form.
            response = send_request_to_nova_server(request_form, self.options['nova_server'])
            if bool(json.loads(response)['success']):
                print("Job " + request_form['jobID'] + " sent to nova-server")

            pool = ThreadPool(processes=1)
            thread = pool.apply_async(check_nova_server_status, (request_form['jobID'], self.options['nova_server']))
            print("Wait for results of NOVA-Server...")
            result = thread.get()
            return str(result)

        except Exception as e:
            raise Exception(e)
