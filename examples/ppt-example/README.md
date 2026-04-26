# PPT Generation Example

> **Agent**: `ppt-agent`  
> **Capability**: Presentation generation from structured outlines  
> **Level**: L1 MVP

---

## Objective

Demonstrate the ppt-agent's ability to convert a structured presentation outline into a complete PowerPoint file with proper formatting, layouts, and styling.

---

## Input

- **File**: `presentation-outline.json` — Structured presentation content
- **Format**: JSON with slides array

### Sample Input Structure

```json
{
  "title": "Q4 Engineering Review",
  "author": "Engineering Team",
  "slides": [
    {
      "type": "title",
      "title": "Q4 Engineering Review",
      "subtitle": "October - December 2024"
    },
    {
      "type": "content",
      "title": "Key Achievements",
      "bullets": [
        "Shipped v2.0 with 99.9% uptime",
        "Reduced latency by 40%",
        "Onboarded 5 enterprise customers"
      ]
    },
    {
      "type": "chart",
      "title": "Performance Metrics",
      "chart_type": "bar",
      "data": {
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "values": [85, 92, 88, 97]
      }
    }
  ]
}
```

---

## Expected Output

- **File**: `artifacts/slides.pptx`
- **Format**: Microsoft PowerPoint (.pptx)
- **Contents**:
  - Title slide with presentation title and subtitle
  - Content slides with bullet points
  - Chart slides with data visualizations
  - Consistent theme and formatting

### Output Quality Criteria

- [ ] File opens correctly in PowerPoint/Google Slides
- [ ] All slides from outline are present
- [ ] Title slide has correct title/subtitle
- [ ] Content slides have proper bullet formatting
- [ ] Total slide count matches outline

---

## Running the Example

```powershell
# Navigate to project root
cd kimi-production-grade-agent-pack

# Activate virtual environment
.venv\Scripts\activate

# Note: slide-maker is L2 (planned); use production coordinator
kimi --agent-file agents/production-coordinator.yaml --prompt (Get-Content examples/ppt-example/presentation-outline.json -Raw)
```

---

## Verification

```powershell
# Check output exists
Get-ChildItem -Path 'artifacts/slides.pptx'

# Verify file size (should be > 10KB)
stat -c "%s" artifacts/slides.pptx

# List slides using python-pptx (optional)
python -c "
from pptx import Presentation
prs = Presentation('artifacts/slides.pptx')
print(f'Slides: {len(prs.slides)}')
for i, slide in enumerate(prs.slides):
    title = slide.shapes.title.text if slide.shapes.title else 'No title'
    print(f'  Slide {i+1}: {title}')
"```

---

## Notes

- Install `python-pptx` dependency: `pip install python-pptx`
- Chart slides require matplotlib for image generation
- Custom themes can be specified with `--theme` option
- Maximum recommended slide count: 50
