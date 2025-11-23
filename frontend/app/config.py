import json
from pathlib import Path

CONFIG_PATH = Path("config.json")

class ConfigManager:
    DEFAULTS = {
        "App": {
            "name": {
                "value": "iCal Server",
                "type": "text"
            },
            "default_calendar": {
                "value": "/admin/calendar.ics",
                "type": "text"
            }
        }
    }
    
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.config = {}
        self.load()

    def load(self):
        if self.path.exists():
            with open(self.path, "r") as f:
                self._config = json.load(f)

        else:
            # Populate defaults
            self._config = self.DEFAULTS.copy()
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get_sections(self):
        return list(self._config.keys())

    def get_section(self, section):
        return self._config.get(section, {})

    def get_fields(self, section):
        return self._config.get(section, {}).items()

    def get(self, section, field):
        return self._config[section][field]["value"]

    def update_from_form(self, form_data: dict):
        """Update config values using submitted form data."""
        for key, value in form_data.items():
            # Key format: Section:Field
            if ":" not in key:
                continue
            
            section, field = key.split(":", 1)
            if section not in self._config or field not in self._config[section]:
                continue

            field_meta = self._config[section][field]
            ftype = field_meta.get("type", "text")

            # Normalize values by type
            if ftype == "bool":
                value = value.lower() == "true"
            elif ftype == "number":
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
            elif ftype == "select":
                if value not in field_meta.get("options", []):
                    continue

            field_meta["value"] = value

        self.save()

config = ConfigManager()
        
