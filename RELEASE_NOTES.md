# Release Notes — Kimi Production-Grade Agent Pack v1.3.0

**Release Version**: v1.3.0  
**Release Codename**: L1 MVP  
**Status**: Production Ready  
**Previous Version**: v1.2.0

---

## Highlights

This release marks the **L1 Minimum Viable Product (MVP)** milestone for the Kimi Production-Grade Agent Pack. It includes a complete documentation suite, automated release tooling, and a comprehensive regression testing framework.

### Key Achievements

- **Complete documentation**: README, QUICKSTART, TROUBLESHOOTING, CHANGELOG
- **5 L1 Agents**: Deep Research, PPT Generation, Spreadsheet, Codebase Fix, Document-to-Skill
- **Automated release pipeline**: Check, regression, package, and cleanup scripts
- **Error taxonomy**: 10 well-documented error codes with resolution steps
- **Usability validation**: Structured log template for acceptance testing

---

## What's New

### Documentation
- **README.md** — Comprehensive project guide with installation, usage, and examples
- **QUICKSTART.md** — 7-step getting started guide with copy-paste commands
- **TROUBLESHOOTING.md** — Full error taxonomy (E001-E010) with debug techniques
- **CHANGELOG.md** — Version history from v1.0.0 to v1.3.0

### Scripts & Tooling
- `scripts/release_check.py` — Validate release readiness with `--level l1` and `--strict`
- `scripts/regression_runner.py` — Execute regression suites and generate reports
- `scripts/package_l1_release.py` — Package releases with manifest and zip generation
- `scripts/clean_runtime_artifacts.py` — Safe cleanup with dry-run default

### Testing & Validation
- L1 Regression Suite with task suite YAML configuration
- Integration smoke runner with pass/fail/hard_fail tracking
- Unit-smoke test cards for individual component validation
- Usability validation log template for acceptance testing

### Examples
- README files for all 5 example directories
- Input/output specifications for each agent use case
- Run commands and expected results

---

## System Requirements

- Python 3.11 or higher
- Kimi Code CLI (latest stable)
- 500MB disk space (2GB recommended)
- 4GB RAM (8GB recommended)

---

## Installation

```powershell
git clone <repository-url>
cd kimi-production-grade-agent-pack
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/release_check.py --level l1```

---

## Known Limitations

1. **E001 (SDK Unavailable)**: CLI fallback is automatic but may have reduced functionality
2. **E009 (Sandbox Timeout)**: Default 60s timeout may need adjustment for large codebases
3. **L2 Agents**: Not yet available in this release
4. **Windows Native**: Native Windows, macOS, and WSL supported

---

## Upgrade Notes

No upgrade steps required for fresh installations.

From v1.2.0:
```powershell
git pull origin main
pip install -r requirements.txt
python scripts/release_check.py --strict```

---

## Verification Checklist

Before using this release, verify:

- [ ] `python scripts/release_check.py --level l1` returns exit code 0
- [ ] Unit-smoke tests pass: `python -m pytest evals/unit-smoke/ -v`
- [ ] Integration-smoke tests pass: `python evals/integration-smoke-runner.py`
- [ ] At least one example runs successfully (see `examples/`)

---

## Feedback & Support

- Issues: File a bug report with `runtime/errors.jsonl` and `runtime/debug.log`
- Questions: See TROUBLESHOOTING.md for common issues
- Contributing: See README.md contribution guidelines

---

*This release represents the L1 MVP milestone. The foundation is solid and ready for production use.*
