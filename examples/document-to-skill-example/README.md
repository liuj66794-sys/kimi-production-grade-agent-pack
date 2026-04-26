# Document-to-Skill Example

> **Agent**: `document-to-skill`  
> **Capability**: Convert documents (API docs, guides) into executable skill specifications  
> **Level**: L1 MVP

---

## Objective

Demonstrate the document-to-skill agent's ability to parse a document (API reference, user guide, etc.) and convert it into a structured, executable skill specification with proper frontmatter, parameters, and implementation.

---

## Input

- **File**: `api-doc.md` — Document to convert
- **Format**: Markdown document describing an API or process

### Sample Input (api-doc.md)

```markdown
# Weather API

Get current weather and forecasts for any location.

## Endpoint: GET /weather/current

Parameters:
- `location` (string, required): City name or coordinates
- `units` (string, optional): "metric" or "imperial", default "metric"

Response:
```json
{
  "temperature": 22.5,
  "humidity": 65,
  "conditions": "partly_cloudy",
  "wind_speed": 12.3
}
```

## Endpoint: GET /weather/forecast

Parameters:
- `location` (string, required): City name or coordinates
- `days` (integer, optional): Number of days (1-7), default 3

Returns forecast data for the specified number of days.
```

---

## Expected Output

- **Skill Directory**: `skills/new-skill/` — Generated skill containing:
  - `skill.yaml` — Skill specification with frontmatter
  - `README.md` — Skill documentation
  - `schema.json` — Input/output JSON schema
  - `implementation.md` — Implementation notes

### Sample Output Structure

```
skills/new-skill/
├── skill.yaml           # Skill spec with name, version, params
├── README.md            # Usage documentation
├── schema.json          # JSON schema for inputs/outputs
└── implementation.md    # Implementation guide
```

### Output Quality Criteria

- [ ] Skill has valid YAML frontmatter (name, version, description)
- [ ] All API endpoints are represented as skill actions
- [ ] Parameters have correct types and required/optional flags
- [ ] JSON schema validates against inputs
- [ ] README contains usage examples
- [ ] Implementation notes are actionable

---

## Running the Example

```powershell
# Navigate to project root
cd kimi-production-grade-agent-pack

# Activate virtual environment
.venv\Scripts\activate

# Run with production coordinator
kimi --agent-file agents/production-coordinator.yaml --prompt (Get-Content examples/document-to-skill-example/api-doc.md -Raw)
```

---

## Verification

```powershell
# Check output directory exists
Get-ChildItem -Path 'skills/new-skill/'

# Validate YAML frontmatter
python -c "
import yaml
with open('skills/new-skill/skill.yaml') as f:
    spec = yaml.safe_load(f)
print(f\"Name: {spec.get('name', 'MISSING')}\")
print(f\"Version: {spec.get('version', 'MISSING')}\")
print(f\"Description: {spec.get('description', 'MISSING')[:100]}...\")
print(f\"Parameters: {list(spec.get('parameters', {}).keys())}\")
"

# Validate JSON schema
python -c "
import json, jsonschema
with open('skills/new-skill/schema.json') as f:
    schema = json.load(f)
print(f\"Schema type: {schema.get('type', 'MISSING')}\")
print(f\"Properties: {list(schema.get('properties', {}).keys())}\")
"

# Check README exists and has content
(Get-Content 'skills/new-skill/README.md```').Length
---

## Notes

- The agent works best with structured documents (API refs, guides with clear sections)
- Free-form documents may require manual cleanup of the output
- Output skill directory is created fresh; use `--merge` to update existing skills
- Review generated schemas for accuracy before using in production
- The conversion quality depends on document structure clarity
