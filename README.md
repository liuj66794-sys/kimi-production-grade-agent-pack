# Kimi Production-Grade Agent Pack

> **Version**: v1.3.0 (L1 MVP Release)  
> **License**: MIT  
> **Python**: 3.11+

---

## Overview

Kimi Production-Grade Agent Pack is a comprehensive agent-based automation framework designed for production environments. It provides a structured architecture for defining, executing, and evaluating intelligent agents with robust error handling, evidence tracking, and quality assurance gates.

This pack includes:

- **Agent definitions** with skill bindings and capability declarations
- **Skill specifications** with executable code and validation schemas
- **Evaluation framework** for unit-smoke and integration-smoke testing
- **Error taxonomy** with structured error envelopes and recovery strategies
- **Release tooling** for check, regression, packaging, and cleanup

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.11 | 3.12 |
| OS | Windows / macOS / Linux | Windows 11 / macOS 14+ / Ubuntu 22.04 |
| Disk | 500MB | 2GB |
| Memory | 4GB | 8GB |
| Kimi Code CLI | Latest stable | Latest stable |

---

## Installation

### 1. Clone the Repository

```powershell
git clone <repository-url> kimi-production-grade-agent-pack
cd kimi-production-grade-agent-pack```

### 2. Create Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate```

### 3. Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt```

### 4. Verify Installation

```powershell
python scripts/release_check.py --level l1```

Expected output: All checks PASS with exit code 0.

---

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for a step-by-step guide to get up and running in 5 minutes.

**TL;DR:**

```powershell
# Run unit-smoke tests
python -m pytest evals/unit-smoke/ -v

# Run integration-smoke tests
python evals/integration-smoke-runner.py

# Run release check
python scripts/release_check.py --level l1```

---

## Directory Structure

```
kimi-production-grade-agent-pack/
├── README.md                 # This file
├── QUICKSTART.md            # Getting started guide
├── CHANGELOG.md             # Version history
├── RELEASE_NOTES.md         # Current release notes
├── TROUBLESHOOTING.md       # Error diagnosis guide
├── DESIGN.md                # Architecture design document
├── AGENTS.md                # Agent catalog
├── SKILL.md                 # Skill specification format
├── VERSION                  # Current version file
├── requirements.txt         # Python dependencies
│
├── agents/                  # Agent definitions
│   ├── deep-research.yaml
│   ├── ppt-agent.yaml
│   ├── spreadsheet-agent.yaml
│   ├── codebase-fix-agent.yaml
│   └── document-to-skill.yaml
│
├── skills/                  # Skill specifications
│   ├── deep-research/
│   ├── ppt-generation/
│   ├── spreadsheet/
│   ├── codebase-fix/
│   └── document-conversion/
│
├── schemas/                 # JSON schemas
│   ├── error-envelope.json
│   ├── task-event.json
│   ├── evidence-synthesis.json
│   └── qa-gate-result.json
│
├── scripts/                 # Automation scripts
│   ├── release_check.py
│   ├── regression_runner.py
│   ├── package_l1_release.py
│   └── clean_runtime_artifacts.py
│
├── evals/                   # Evaluation framework
│   ├── unit-smoke/
│   ├── integration-smoke-runner.py
│   ├── task-suite.yaml
│   └── results/
│
├── examples/                # Usage examples
│   ├── deep-research-example/
│   ├── ppt-example/
│   ├── spreadsheet-example/
│   ├── codebase-fix-example/
│   └── document-to-skill-example/
│
├── docs/                    # Additional documentation
│   └── v1.3-usability-log.md
│
├── runtime/                 # Runtime temp files (gitignored)
└── artifacts/               # Generated artifacts (gitignored)
```

---

## Usage Examples

### Example 1: Run a Deep Research Task

```powershell
# Run with researcher sub-agent
kimi --agent-file agents/researcher-sub.yaml --prompt (Get-Content "research-topic.txt" -Raw)

# Or with production coordinator for full orchestration
kimi --agent-file agents/production-coordinator.yaml --prompt (Get-Content "research-topic.txt" -Raw)
```

### Example 2: Generate a Presentation

```powershell
# Note: slide-maker is L2 (planned); for now use production coordinator
kimi --agent-file agents/production-coordinator.yaml --prompt (Get-Content "presentation-outline.json" -Raw)
```

### Example 3: Fix Codebase Issues

```powershell
kimi --agent-file agents/coder-sub.yaml --prompt "Review and fix issues in codebase-dir/"
```

### Example 4: Convert Document to Skill

```powershell
kimi --agent-file agents/production-coordinator.yaml --prompt (Get-Content "api-doc.md" -Raw)
```

---

## Agent Catalog

| Agent | Capability | Status | Description |
|-------|-----------|--------|-------------|
| `deep-research` | Research | L1 MVP | Deep multi-source research with synthesis |
| `ppt-agent` | Content Gen | L1 MVP | Presentation generation from outlines |
| `spreadsheet-agent` | Data Processing | L1 MVP | Spreadsheet analysis and transformation |
| `codebase-fix` | Code Analysis | L1 MVP | Automated codebase issue detection and fix |
| `document-to-skill` | Conversion | L1 MVP | Convert documents to executable skills |

See [AGENTS.md](AGENTS.md) for full agent specifications.

---

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Make** your changes with tests
4. **Run** the regression suite: `python scripts/regression_runner.py --suite l1-regression`
5. **Commit** with clear messages
6. **Push** and create a Pull Request

### Contribution Guidelines

- Follow PEP 8 for Python code
- Add tests for new features
- Update documentation for user-facing changes
- Ensure `release_check.py --strict` passes
- Reference related issue numbers in PRs

---

## Version History

| Version | Date | Milestone |
|---------|------|-----------|
| v1.0.0 | - | Product Blueprint |
| v1.1.0 | - | Technical Pre-research |
| v1.2.0 | - | Integration Validation |
| v1.3.0 | Current | L1 MVP Release |

See [CHANGELOG.md](CHANGELOG.md) for detailed release history.

---

## Troubleshooting

If you encounter issues, please check:

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common errors and solutions
2. `runtime/debug.log` - Debug log output
3. `runtime/errors.jsonl` - Structured error records
4. `runtime/task-events/` - Task execution events

---

## License

MIT License - see LICENSE file for details.

---

*Built with Kimi Code CLI. For production-grade agent automation.*
