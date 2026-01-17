# Prompt Manager

A personal prompt management system with REST API and CLI for storing, querying, and retrieving prompts with full metadata tracking and Jinja2 templating support.

## Features

- **REST API**: Full CRUD operations with FastAPI
- **CLI**: Typer-based command-line interface
- **Template Support**: Jinja2 templating with variable extraction
- **Pipe-friendly**: Read stdin into templates, pipe output to other commands (e.g., Claude)
- **Aliases**: Create shortcuts like `pmge` for `pm get explain-error`
- **Version History**: Track changes to prompts over time
- **Search & Filter**: Full-text search, category and tag filtering
- **Usage Statistics**: Track prompt usage and popularity
- **Notes**: Add success/failure notes to prompts

## Installation

```bash
# Install with pip (in a virtual environment)
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# For PostgreSQL support
pip install -e ".[postgres]"
```

### System-wide Installation (with pipx)

```bash
# Install globally with pipx (recommended for CLI usage)
pipx install /path/to/prompt-manager

# Or if already installed, reinstall to pick up changes
pipx install --force /path/to/prompt-manager
```

## Quick Start

### Initialize Database

```bash
pm init-db
```

### Start API Server

```bash
pm serve
# Or with auto-reload for development
pm serve --reload
```

### CLI Usage

```bash
# Add a prompt
pm add my-prompt --title "My Prompt" --content "Hello world"

# Add from file
pm add code-review --title "Code Review" --from-file review.txt

# Add from pipe
echo "Review this code: {{code}}" | pm add code-review --title "Code Review"

# Get a prompt
pm get my-prompt

# Get with JSON output
pm get my-prompt --json

# Render template
pm get code-review --var code="print('hello')"

# List prompts
pm list
pm list --category code
pm list --tags python,api
pm list --sort popular

# Search
pm search "code review"

# Edit in $EDITOR
pm edit my-prompt

# Delete
pm delete my-prompt

# View history
pm history my-prompt

# Restore version
pm restore my-prompt --version 1

# Add notes
pm note my-prompt --success "Worked great for X"
pm note my-prompt --failure "Didn't work for Y"

# View statistics
pm stats
pm categories
pm tags

# Get random prompt
pm random
pm random --category code

# Alias management
pm alias add pmge explain-error     # Create shortcut
pm alias list                       # Show all aliases
pm alias remove pmge                # Delete alias
pm alias suggest                    # Show frequently used prompts
pm alias install pmge               # Install as ~/.local/bin/pmge
pm alias sync                       # Install all aliases as scripts
pm alias export                     # Output shell alias definitions
```

### Aliases

Create shortcuts for frequently used prompts:

```bash
# Register an alias
pm alias add pmge explain-error

# Install as executable wrapper script
pm alias install pmge
# Now you can run: pmge --stdin error < error.txt

# Or export shell aliases to your config
pm alias export >> ~/.bashrc

# Install all aliases as wrapper scripts
pm alias sync
```

Wrapper scripts work in non-interactive contexts (scripts, cron, pipes) unlike shell aliases.

### Piping to Other Commands (e.g., Claude)

The CLI supports reading from stdin, making it easy to pipe content through prompts to other commands:

```bash
# Method 1: --stdin flag (fill a template variable from stdin)
cat error.txt | pm get explain-error --stdin error
echo "my code" | pm get review-code --stdin code | claude -p

# Method 2: --var with - (same as above, different syntax)
cat error.txt | pm get explain-error --var error=-

# Method 3: --append (append stdin to any prompt)
cat error.txt | pm get debug-help --append | claude -p
```

**Example workflow:**

```bash
# Create a prompt template
pm add explain-error --title "Explain Error" \
  --content "Help me understand and fix this error:\n\n{{error}}" \
  --category debugging

# Use it with piped input
./my-script.sh 2>&1 | pm get explain-error --stdin error | claude -p

# Or capture and pipe an error
python buggy.py 2>&1 | pm get explain-error --stdin error | claude -p
```

| Method | Use Case | Example |
|--------|----------|---------|
| `--stdin VAR` | Fill template variable from stdin | `cat err.txt \| pm get my-prompt --stdin error` |
| `--var VAR=-` | Same as above, alternative syntax | `cat err.txt \| pm get my-prompt --var error=-` |
| `--append` | Append stdin to prompt output | `cat err.txt \| pm get simple-prompt --append` |

## API Endpoints

### Prompts

```
POST   /api/v1/prompts              # Create prompt
GET    /api/v1/prompts/{slug}       # Get by slug
PUT    /api/v1/prompts/{slug}       # Update prompt
DELETE /api/v1/prompts/{slug}       # Delete prompt
GET    /api/v1/prompts/{slug}/render # Render template
```

### Search & Discovery

```
GET    /api/v1/prompts              # List (with filtering)
GET    /api/v1/prompts?category=x   # Filter by category
GET    /api/v1/prompts?tags=a,b     # Filter by tags
GET    /api/v1/prompts?q=search     # Full-text search
GET    /api/v1/random               # Random prompt
```

### Version History

```
GET    /api/v1/prompts/{slug}/versions      # List versions
GET    /api/v1/prompts/{slug}/versions/{v}  # Get version
POST   /api/v1/prompts/{slug}/versions/{v}/restore # Restore
```

### Statistics

```
GET    /api/v1/stats                # Usage statistics
GET    /api/v1/categories           # List categories
GET    /api/v1/tags                 # List tags
```

## Configuration

### Environment Variables

```bash
# API Server
PM_API_KEY=your-secret-key       # Required for non-localhost
PM_DATABASE_URL=sqlite+aiosqlite:///./prompts.db
PM_HOST=0.0.0.0
PM_PORT=8000

# CLI
PM_API_URL=http://localhost:8000
PM_DEFAULT_FORMAT=plain
PM_EDITOR=vim
```

### CLI Configuration

```bash
pm config show                   # Show configuration
pm config set api-url <url>      # Set API URL
pm config set api-key <key>      # Set API key
pm config set editor nano        # Set editor
```

Configuration file location: `~/.config/prompt-manager/config.toml`

## Data Model

### Prompt Fields

| Field | Type | Description |
|-------|------|-------------|
| slug | string | Unique identifier (URL-safe) |
| title | string | Display name |
| content | text | Prompt content (may contain Jinja2) |
| description | text | Optional description |
| category | string | Primary category |
| tags | list | Searchable tags |
| is_template | bool | Whether content has variables |
| template_vars | dict | Schema of expected variables |
| usage_count | int | Times retrieved |
| success_notes | text | What worked well |
| failure_notes | text | What didn't work |
| version | int | Current version number |

## Development

### Run Tests

```bash
pytest -v
pytest --cov=prompt_manager
```

### Code Quality

```bash
ruff check src tests
mypy src
```

## License

MIT
