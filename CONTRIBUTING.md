# Contributing to MacroClaw

Thank you for your interest in contributing to MacroClaw. This guide covers the key workflows and conventions for the project.

---

## Table of Contents

- [Capturing Reference Screenshots for SikuliX](#capturing-reference-screenshots-for-sikulix)
- [Adding New Export Types](#adding-new-export-types)
- [Extending the DuckDB Schema](#extending-the-duckdb-schema)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)

---

## Capturing Reference Screenshots for SikuliX

SikuliX matches UI elements by comparing screen regions against reference `.png` images. Because each user's display resolution, macOS appearance, and app version may differ, reference screenshots are git-ignored and must be captured locally. However, if you are adding automation for a **new** UI flow, you should document the required screenshots in the SikuliX script comments so other users know what to capture.

### How to capture screenshots

1. Open the SikuliX IDE:
   ```bash
   java -jar sikuli/sikulixide-2.0.6.jar
   ```

2. Open the relevant `.sikuli` script (e.g., `sikuli/export.sikuli`).

3. Click the camera icon in the SikuliX toolbar to enter capture mode.

4. Select the smallest bounding box that uniquely identifies the target UI element. Tips:
   - Include enough surrounding context to avoid ambiguous matches, but not so much that minor layout shifts cause failures.
   - For buttons, capture the button label and a small amount of the button border.
   - For menu items, capture the text and its immediate background.
   - Avoid capturing dynamic content such as dates, counts, or progress indicators.

5. Save the captured image with a descriptive name using snake_case (e.g., `btn_export_all_data.png`, `menu_profile.png`, `dialog_save_confirm.png`).

6. Place all images in `sikuli/images/`.

7. Reference the image filename in the SikuliX script and add a comment describing what it targets:
   ```python
   # btn_export_all_data.png -- The "Export All Data" button on the Settings > Export screen
   click("btn_export_all_data.png")
   ```

### Testing your screenshots

Always test new screenshots with a dry run before committing the script changes:

```bash
python3 scripts/run_export.py --mode daily --dry-run
```

Watch the SikuliX log output for match confidence scores. A score below 0.80 suggests the reference image may need to be re-captured with tighter or wider bounds.

---

## Adding New Export Types

MacroClaw currently supports two export types: daily nutrition/weight data and workout data. To add a new export type (for example, a new data category that MacroFactor adds in a future update):

### 1. Create the SikuliX automation flow

- Add a new `.sikuli` script in `sikuli/` or extend the existing `export.sikuli` script.
- Document every UI element that needs to be clicked, including the expected screenshot filenames.
- Follow the existing pattern of waiting for elements with a configurable timeout before clicking.

### 2. Define the parser

- Add a new parsing function in `scripts/parse_xlsx.py` or create a new parser module in `scripts/`.
- The parser should:
  - Accept a file path to the `.xlsx` export.
  - Read and normalize column names (strip whitespace, lowercase, replace spaces with underscores).
  - Handle missing or optional columns gracefully.
  - Return a list of dictionaries or a pandas/polars DataFrame ready for DuckDB insertion.

### 3. Update the DuckDB schema

- Add the new table definition to `scripts/schema.sql`.
- Ensure the table has a composite primary key or unique constraint that supports idempotent upserts.
- See the [Extending the DuckDB Schema](#extending-the-duckdb-schema) section below.

### 4. Register the export mode

- Update `scripts/run_export.py` to accept the new export type via the `--mode` flag or a new flag.
- Update `config/config.example.yaml` with any new configuration keys.

### 5. Update the OpenClaw skill

- Extend `skills/macroclaw_query.py` to include the new table in its schema awareness so the agent can query the new data.

### 6. Write tests

- Add unit tests in `tests/` for the new parser.
- Include at least one test with a sample `.xlsx` fixture to validate column mapping and data types.

---

## Extending the DuckDB Schema

The DuckDB schema is defined in `scripts/schema.sql` and applied by the parser on startup if the tables do not yet exist.

### Guidelines for schema changes

1. **Always add, never remove.** Removing or renaming columns is a breaking change. If a column is no longer populated by MacroFactor, mark it as nullable and document its deprecation in a comment.

2. **Use appropriate types.** DuckDB supports `DATE`, `TIMESTAMP`, `DOUBLE`, `INTEGER`, `VARCHAR`, and `BOOLEAN` among others. Prefer `DOUBLE` over `FLOAT` for numeric precision. Use `DATE` for day-level data.

3. **Define primary keys.** Every table must have a primary key or unique constraint that enables idempotent upserts. For daily data, `date` is typically the primary key. For workout data, use a composite key of `(date, exercise_name, set_number)` or similar.

4. **Write a migration.** If you are modifying an existing table, add an `ALTER TABLE` statement in a new migration file under `scripts/migrations/` with a sequential numeric prefix (e.g., `001_add_sodium_column.sql`). The migration runner applies these in order and tracks which have been applied.

5. **Update the example config.** If the schema change introduces new configuration (e.g., a new column mapping), update `config/config.example.yaml`.

### Example: adding a new column

```sql
-- scripts/migrations/002_add_fiber_column.sql
ALTER TABLE daily_nutrition ADD COLUMN IF NOT EXISTS fiber_g DOUBLE;
```

---

## Code Style

### Python

- **Formatter:** All Python code must be formatted with [Black](https://github.com/psf/black) using the default configuration (line length 88).
- **Linter:** Run [Ruff](https://github.com/astral-sh/ruff) for linting. The project configuration is in `pyproject.toml`.
- **Type hints:** Use type hints for all function signatures. Prefer built-in generics (`list[str]`, `dict[str, int]`) over `typing` module equivalents where Python 3.11+ allows.
- **Docstrings:** Use Google-style docstrings for all public functions and classes.
- **Imports:** Group imports in the standard order: stdlib, third-party, local. Let Ruff's isort rule handle sorting.

### SikuliX scripts

- Add a comment above every `click()`, `wait()`, or `type()` call describing the target element and the expected screenshot filename.
- Use `wait()` with the configured timeout before every `click()` to handle app loading delays.
- Wrap each automation step in a try/except that logs the failure and captures a debug screenshot on error.

### SQL

- Use uppercase for SQL keywords (`SELECT`, `CREATE TABLE`, `INSERT`).
- Use lowercase snake_case for table and column names.
- One column definition per line in `CREATE TABLE` statements.

### General

- No trailing whitespace.
- Files must end with a single newline.
- Use descriptive variable and function names. Avoid single-letter variables except in trivial loops.

---

## Pull Request Process

### Before you start

1. Open an issue describing the change you want to make, unless one already exists.
2. Fork the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Development workflow

1. Make your changes, following the code style guidelines above.
2. Format your Python code:
   ```bash
   black scripts/ skills/ tests/
   ```
3. Lint your code:
   ```bash
   ruff check scripts/ skills/ tests/
   ```
4. Run the test suite:
   ```bash
   pytest tests/
   ```
5. If you modified the DuckDB schema, verify it against a fresh database:
   ```bash
   python3 scripts/parse_xlsx.py --init-schema
   ```

### Submitting the pull request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
2. Open a pull request against `main` on the upstream repository.
3. Fill out the PR template, including:
   - A description of what the change does and why.
   - Steps to test the change.
   - Whether new reference screenshots are needed (and if so, document them).
4. Ensure all CI checks pass (formatting, linting, tests).

### Review and merge

- At least one maintainer must approve the PR before it is merged.
- PRs are merged via squash-and-merge to keep the commit history clean.
- After merging, the feature branch is deleted.

### Reporting issues

When reporting a bug, please include:

- Your macOS version and Mac model (Intel vs. Apple Silicon).
- MacroFactor app version.
- SikuliX version.
- The relevant section of `logs/macroclaw.log` (set log level to `DEBUG` for maximum detail).
- Screenshots of the UI state when the failure occurred, if applicable.

---

Thank you for helping make MacroClaw better.
