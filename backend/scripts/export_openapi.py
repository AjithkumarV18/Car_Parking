"""Write the generated OpenAPI contract to a versionable JSON artifact."""

import json
from pathlib import Path

from app.main import create_application

if __name__ == "__main__":
    output = Path("docs/openapi.json")
    output.write_text(json.dumps(create_application().openapi(), indent=2), encoding="utf-8")
    print(f"Wrote {output}")
