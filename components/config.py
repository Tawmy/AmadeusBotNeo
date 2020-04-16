import json


class Config:
    def __init__(self, bot_config):
        self.default_language = bot_config.get("default_language", "en")
        self.options = {}
        self.limits = {}

    async def load_config_values(self):
        failed = []
        try:
            with open("values/options.json", 'r') as json_file:
                try:
                    self.options = json.load(json_file)
                except ValueError:
                    failed.append("options")
            with open("values/limits.json", 'r') as json_file:
                try:
                    self.limits = json.load(json_file)
                except ValueError:
                    failed.append("limits")
        except FileNotFoundError as exc:
            failed.append(exc.filename)
        return failed
