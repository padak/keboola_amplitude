# Amplitude Connector: Built on Prometheus Driver System (Keboola)

Production-ready Python driver for exporting event data from Amplitude Analytics into Keboola Storage.

**Built on [Prometheus Driver System](https://www.keboola.com/) - AI-powered system generating fast and reliable Python drivers.**

---

## License

MIT license - Do whatever you want with this driver. We'd love to hear your ideas for improvements.

## Features

- **Amplitude Export API** - Export raw event data (read mode)
- **Amplitude Identify API** - Update user properties (write mode)
- **Automatic Compression Handling** - Handles gzip-compressed responses
- **Flexible Authentication** - API key and/or secret key support
- **Bidirectional** - Both read and write in one component
- **Column Mapping** - Flexible mapping from Keboola tables to Amplitude properties
- **Batch Operations** - Efficient batching (2000 records per request)
- **Unit Tests** - Test suite for driver validation

## Setup

### 1. Get Amplitude Credentials

Go to your Amplitude project settings:
```
https://app.amplitude.com/analytics/{YOUR_ORG}/settings/projects/{PROJECT_ID}/general
```

You'll find:
- **API Key** - Used for reading data
- **Secret Key** - Required for Export API

![Amplitude Project Settings](public/amplitude.png)


## Usage

### Keboola Configuration

1. **Create Custom Python Component** in Keboola
2. **Set Git Repository:**
   - URL: `https://github.com/padak/keboola_amplitude.git`
   - Branch: `main`
   - Filename: `main.py`

![Keboola Git Repository Configuration](public/keboola_00.png)

3. **Set User Parameters:**
   ```json
   {
     "#AMPLITUDE_API_KEY": "your_encrypted_api_key",
     "#AMPLITUDE_SECRET_KEY": "your_encrypted_secret_key",
     "amplitude_region": "us",
     "start_date": "20251112T00",
     "end_date": "20251117T23"
   }
   ```
   > Parameters with `#` are encrypted by Keboola automatically

![Keboola User Parameters Configuration](public/keboola_02.png)

4. **Set Output Mapping:**
   - File: `events.csv` → Table: `out.c-amplitude.events`
   - Incremental: ✓ enabled
   - Primary Key: `event_id`

![Keboola Output Mapping Configuration](public/keboola_01.png)

5. **Run** the component

---

## Write Mode: Update User Properties

You can also use this component to send enriched user properties from Keboola back to Amplitude (e.g., CLV, segments, ML predictions).

### Configuration for Write Mode

1. **Prepare Input Table** in Keboola with user properties:
   - Must have: user ID column (e.g., `customer_id`)
   - Columns to map: any custom properties (e.g., `lifetime_value`, `segment`, `churn_risk`)

2. **Set Input Mapping:**
   - Map your table → component input

3. **Set User Parameters:**
   ```json
   {
     "#AMPLITUDE_API_KEY": "your_encrypted_api_key",
     "user_id_column": "customer_id",
     "property_columns": {
       "lifetime_value": "customer_lifetime_value",
       "segment": "ltv_segment",
       "churn_risk": "churn_risk_score"
   }
   ```

4. **Run** the component

### Example: Send CLV and Segments

**Input table in Keboola:**

```
customer_id,lifetime_value,segment,churn_risk
user_123,4567.89,high_value,0.12
user_456,1234.56,medium_value,0.45
user_789,789.99,low_value,0.78
```

**Configuration:**
```json
{
  "#AMPLITUDE_API_KEY": "...",
  "user_id_column": "customer_id",
  "property_columns": {
    "lifetime_value": "customer_lifetime_value",
    "segment": "ltv_segment",
    "churn_risk": "churn_risk_score"
  }
}
```

**Result in Amplitude:**
- User `user_123` gets properties: `{customer_lifetime_value: 4567.89, ltv_segment: "high_value", churn_risk_score: 0.12}`
- Properties available for segmentation and analysis

### Bidirectional Usage

You can configure both read and write in the same component:

```json
{
  "#AMPLITUDE_API_KEY": "...",
  "#AMPLITUDE_SECRET_KEY": "...",

  // Read: export events
  "start_date": "20251117T00",
  "end_date": "20251117T23",

  // Write: update user properties
  "user_id_column": "customer_id",
  "property_columns": {
    "lifetime_value": "customer_lifetime_value",
    "segment": "ltv_segment"
  }
}
```

The component will:
1. Export events to `out.c-amplitude.events` (read)
2. Update user properties from input table (write)

