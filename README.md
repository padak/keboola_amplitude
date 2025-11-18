# Amplitude Analytics Driver for Keboola

Production-ready Python driver for exporting event data from Amplitude Analytics into Keboola Storage.

## Features

- **Amplitude Export API** - Export raw event data
- **Automatic Compression Handling** - Handles gzip-compressed responses
- **Flexible Authentication** - API key and/or secret key support
- **Keboola Integration** - Custom Python component ready for deployment
- **Comprehensive Tests** - Full test suite included

## Setup

### 1. Get Amplitude Credentials

Go to your Amplitude project settings:
```
https://app.amplitude.com/analytics/{YOUR_ORG}/settings/projects/{PROJECT_ID}/general
```

You'll find:
- **API Key** - Used for reading data
- **Secret Key** - Required for Export API

### 2. Environment Variables

Create `.env` file (not committed to git):
```bash
AMPLITUDE_API_KEY=your_api_key_here
AMPLITUDE_SECRET_KEY=your_secret_key_here
AMPLITUDE_REGION=us  # or eu
```

### 3. Install Dependencies

```bash
uv pip install -r pyproject.toml
```

## Usage

### Keboola Custom Python Component

Configure in Keboola UI:

```json
{
  "parameters": {
    "source": "git",
    "venv": "3.13",
    "git": {
      "url": "https://github.com/padak/keboola_amplitude.git",
      "branch": "main",
      "filename": "main.py",
      "auth": "none"
    },
    "user_properties": {
      "#amplitude_api_key": "your_encrypted_key",
      "#amplitude_secret_key": "your_encrypted_secret",
      "amplitude_region": "us",
      "start_date": "20251112T00",
      "end_date": "20251117T23"
    }
  }
}
```

Output mapping:
- **File**: `events.csv`
- **Source**: `out/tables/events.csv`
- **Destination**: `out.c-amplitude.events`

### Local Testing

```bash
# Export test data
python scripts/export_nov_12_data.py

# Generate sample data to Amplitude
python scripts/generate_sample_data.py
```

## Project Structure

```
.
├── amplitude_driver/          # Main driver package
│   ├── client.py             # Amplitude API client
│   ├── exceptions.py         # Custom exceptions
│   ├── __init__.py           # Package exports
│   └── tests/                # Test suite
├── main.py                   # Keboola entry point
├── scripts/                  # Development utilities
│   ├── generate_sample_data.py
│   └── export_nov_12_data.py
├── docs/                     # Documentation
├── pyproject.toml            # Project configuration
└── uv.lock                   # Dependency lock file
```

## API Reference

### AmplitudeDriver

```python
from amplitude_driver import AmplitudeDriver

# Initialize from environment
client = AmplitudeDriver.from_env()

# Export events
events = client.read_events_export(
    start='20251112T00',
    end='20251117T23'
)

# Get event schema
schema = client.get_event_schema()
```

## Data Retention

⚠️ **Important**: Amplitude stores raw event data for ~3-7 days. For older data, use Amplitude's other APIs or export regularly and store in Keboola.

## License

MIT
