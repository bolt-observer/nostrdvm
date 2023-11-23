import json
from threading import Thread

from utils.admin_utils import AdminConfig
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Announcement
from dvm import DVM


class DVMTaskInterface:
    NAME: str
    KIND: int
    TASK: str
    COST: int
    PK: str
    DVM = DVM
    dvm_config: DVMConfig
    admin_config: AdminConfig

    def NIP89_announcement(self, d_tag, content):
        nip89 = NIP89Announcement()
        nip89.name = self.NAME
        nip89.kind = self.KIND
        nip89.pk = self.PK
        nip89.dtag = d_tag
        nip89.content = content
        return nip89

    def run(self):
        nostr_dvm_thread = Thread(target=self.DVM, args=[self.dvm_config, self.admin_config])
        nostr_dvm_thread.start()

    def is_input_supported(self, input_type, input_content) -> bool:
        """Check if input is supported for current Task."""
        pass

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None) -> dict:
        """Parse input into a request form that will be given to the process method"""
        pass

    def process(self, request_form):
        "Process the data and return the result"
        pass

    @staticmethod
    def set_options(request_form):
        print("Setting options...")
        opts = []
        if request_form.get("options"):
            opts = json.loads(request_form["options"])
            print(opts)

        # old format, deprecated, will remove
        elif request_form.get("optStr"):
            opts = []
            for k, v in [option.split("=") for option in request_form["optStr"].split(";")]:
                t = (k, v)
                opts.append(t)
        print("...done.")

        return dict(opts)
