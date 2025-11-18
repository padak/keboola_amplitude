# Amplitude API - CRITICAL FINDINGS

**Analysis Date:** 2025-11-17
**Documentation Source:** https://amplitude.com/docs/apis/analytics
**APIs Analyzed:** 5 (HTTP V2, Batch Upload, Identify, Export, User Profile)

---

## Executive Summary

The Amplitude Analytics APIs are **NOT a single uniform REST API**. They are **5 distinct APIs with completely different authentication methods, request formats, and response structures**.

**⚠️ CRITICAL:** A driver implementation must handle these differences, as failing to do so will cause authentication failures and data loss.

---

## Critical Bug #1: THREE Different Authentication Methods

Amplitude uses **THREE fundamentally different authentication approaches**. A naive implementation that assumes consistent authentication will FAIL.

### Authentication Method Breakdown

#### Method 1: API Key in Request BODY (3 APIs)

**Used by:** HTTP V2 API, Batch Upload API, Identify API

**Header:** `Content-Type: application/json` or `application/x-www-form-urlencoded`

**Authentication:** `api_key` parameter in request body, NOT header

```bash
# HTTP V2 API - JSON body
curl --request POST 'https://api2.amplitude.com/2/httpapi' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "api_key": "YOUR_API_KEY",  # ← API KEY IN BODY
    "events": [...]
  }'

# Identify API - Form encoded body
curl --request POST 'https://api2.amplitude.com/identify' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'api_key=<API-KEY>' \
  --data-urlencode 'identification=[...]'
```

**⚠️ BUG PREVENTION:**
- Do NOT add `Authorization` header for these endpoints
- API key goes in request body as `api_key` parameter
- Content-Type varies: JSON vs form-encoded

#### Method 2: Basic HTTP Authentication (Export API)

**Used by:** Export API

**Header:** `Authorization: Basic {base64-encoded-credentials}`

**Format:** Base64 encode `{api_key}:{secret_key}`

```bash
# Export API - Basic Auth header
curl --request GET 'https://amplitude.com/api/2/export?start=20220101T00&end=20220127T00' \
  -u '{api_key}:{secret_key}'  # ← Creates Authorization: Basic header

# Or explicitly:
curl --request GET 'https://amplitude.com/api/2/export?start=20220101T00&end=20220127T00' \
  --header 'Authorization: Basic YWhhbWwsdG9uQGFwaWdlZS5jb206bClwYXNzdzByZAo'
```

**⚠️ BUG PREVENTION:**
- Use requests-auth with HTTPBasicAuth OR
- Manually encode as `base64(f"{api_key}:{secret_key}")` and set header
- This API requires TWO secrets: api_key AND secret_key

#### Method 3: API Key in Header with "Api-Key" Prefix (User Profile API)

**Used by:** User Profile API

**Header:** `Authorization: Api-Key {secret_key}`

**Format:** "Api-Key" (NOT "Bearer") followed by secret

```bash
# User Profile API - Api-Key header
curl --request GET 'https://profile-api.amplitude.com/v1/userprofile?user_id=12345' \
  --header 'Authorization: Api-Key 1234567890'  # ← "Api-Key" prefix, case-sensitive
```

**⚠️ BUG PREVENTION:**
- Header prefix MUST be "Api-Key" (NOT "Bearer")
- This is case-sensitive: "Api-Key" not "API-Key" or "api-key"
- Only one secret needed (different from Basic Auth)

### Summary Table

| API | Auth Method | Location | Format | Multiple Secrets |
|-----|-------------|----------|--------|------------------|
| HTTP V2 | Body param | `api_key` | `{value}` | No |
| Batch Upload | Body param | `api_key` | `{value}` | No |
| Identify | Form param | `api_key` | `{value}` | No |
| Export | Basic Auth | Header | `Authorization: Basic base64(key:secret)` | **YES** |
| User Profile | Header Api-Key | Header | `Authorization: Api-Key secret` | No |

---

## Critical Bug #2: Content-Type Header Management

**⚠️ NEVER set Content-Type in session headers** for these APIs. Different endpoints require different content types.

### Content-Type by API

| API | HTTP Method | Content-Type | How Set |
|-----|-------------|--------------|---------|
| HTTP V2 | POST | `application/json` | Per-request with `json=data` |
| Batch Upload | POST | `application/json` | Per-request with `json=data` |
| Identify | POST | `application/x-www-form-urlencoded` | Per-request with `data=form_data` |
| Export | GET | None (GET request) | N/A |
| User Profile | GET | None (GET request) | N/A |

**✅ CORRECT Implementation:**
```python
# Don't set Content-Type in session headers
session.headers.update({
    "Accept": "application/json",
    # Content-Type is set per-request!
})

# Per-request:
response = session.post(url, json=data)  # Sets Content-Type: application/json
response = session.post(url, data=form_data)  # Sets Content-Type: application/x-www-form-urlencoded
response = session.get(url)  # No Content-Type
```

**✗ WRONG Implementation:**
```python
# This breaks everything!
session.headers["Content-Type"] = "application/json"  # ← BUG: affects GET requests too
```

---

## Critical Bug #3: API Key Position (Body vs Header)

Most REST APIs use headers for authentication. **Amplitude mostly uses request body.**

### Position by API

| API | Position | Parameter Name |
|-----|----------|-----------------|
| HTTP V2 | **Body** | `api_key` |
| Batch Upload | **Body** | `api_key` |
| Identify | **Body/Form** | `api_key` |
| Export | **Header** | `Authorization` |
| User Profile | **Header** | `Authorization` |

**⚠️ Implication:** Cannot use a single session header approach for all APIs. Must implement per-endpoint authentication.

---

## Critical Bug #4: Response Parsing

Amplitude APIs have different response structures that must be handled carefully.

### Write APIs Response (HTTP V2, Batch Upload)

```json
{
  "code": 200,
  "events_ingested": 123,
  "payload_size_bytes": 4567,
  "server_upload_time": 1639757639123
}
```

**Key Fields:** `events_ingested`, `payload_size_bytes`, `server_upload_time`

### User Profile API Response

```json
{
  "userData": {
    "recommendations": [...],
    "user_id": "12345",
    "device_id": "ffff-ffff-ffff-ffff",
    "amp_props": {...},
    "cohort_ids": [...],
    "propensities": [...]
  }
}
```

**⚠️ BUG PREVENTION:** Response is wrapped in `userData` object. Must extract this.

### Export API Response

```
[Zipped archive of JSON files, one event per line]
```

**⚠️ SPECIAL:** Response is a ZIP file, not JSON. Must decompress before parsing.

### Identify API Response

Documentation doesn't specify response fields explicitly. Status code indicates success/failure.

---

## Critical Bug #5: Rate Limits and Constraints

Each API has different rate limits. Exceeding them causes 429 errors.

### Rate Limits by API

| API | Limit | Value |
|-----|-------|-------|
| HTTP V2 | Events/sec (Starter) | 1,000 |
| HTTP V2 | Payload size | 1 MB |
| HTTP V2 | Events per request | 2,000 |
| Batch Upload | Payload size | 20 MB |
| Batch Upload | Events per request | 2,000 |
| Batch Upload | Daily quota | 500,000 per device/user |
| Identify | Property updates/hour/user | 1,800 |
| Export | Export size | 4 GB |
| User Profile | Requests/minute | 600 |

**⚠️ BUG PREVENTION:**
- Validate payload size before sending (1MB vs 20MB)
- Validate event count before sending (max 2,000)
- Implement exponential backoff on 429 errors
- For Identify: Track property update counts per user per hour

---

## Critical Bug #6: Query Parameters and Formats

### Export API Query Parameters (Time-Based Extraction)

**Required format:** `YYYYMMDDTHH` (Year-Month-Day-Time in hours)

```bash
# CORRECT
curl 'https://amplitude.com/api/2/export?start=20220201T05&end=20220205T23'

# WRONG
curl 'https://amplitude.com/api/2/export?start=2022-02-01&end=2022-02-05'  # Wrong format
curl 'https://amplitude.com/api/2/export?start=20220201T05:00&end=20220205T23:00'  # Wrong format
```

### User Profile API Query Parameters

```bash
# At least one of user_id or device_id required
curl 'https://profile-api.amplitude.com/v1/userprofile?user_id=12345&get_recs=true'
curl 'https://profile-api.amplitude.com/v1/userprofile?device_id=abc-def-ghi&get_amp_props=true'

# Optional combinations
curl 'https://profile-api.amplitude.com/v1/userprofile?user_id=12345&get_recs=true&rec_id=98765'
```

---

## Regional Endpoints

Amplitude provides separate endpoints for EU residency compliance.

### Endpoint URLs

| API | Standard | EU |
|-----|----------|-----|
| HTTP V2 | `https://api2.amplitude.com/2/httpapi` | `https://api.eu.amplitude.com/2/httpapi` |
| Batch Upload | `https://api2.amplitude.com/batch` | `https://api.eu.amplitude.com/batch` |
| Identify | `https://api2.amplitude.com/identify` | `https://api.eu.amplitude.com/identify` |
| Export | `https://amplitude.com/api/2/export` | `https://analytics.eu.amplitude.com/api/2/export` |
| User Profile | `https://profile-api.amplitude.com/v1/userprofile` | N/A |

---

## No Pagination Support

**Important:** Amplitude APIs do NOT support traditional pagination.

- **Write APIs:** No pagination (batch operations only)
- **Export API:** Time-range based extraction (no pagination needed)
- **User Profile API:** Single request per user (no pagination)

**Implication:** Driver should set `pagination: PaginationStyle.NONE`

---

## Capabilities Summary

| Operation | Supported | By API |
|-----------|-----------|--------|
| **Read** | ✅ | Export, User Profile |
| **Write** | ✅ | HTTP V2, Batch Upload |
| **Update** | ✅ | Identify (user property updates) |
| **Delete** | ❌ | None |
| **Batch Operations** | ✅ | HTTP V2 (2000 events), Batch (2000 events), Identify (bulk endpoints) |

---

## Implementation Recommendations

### Option 1: Multi-Endpoint Single Driver

```python
class AmplitudeDriver(BaseDriver):
    """Handles all 5 Amplitude APIs"""

    def read_events_export(self, start: str, end: str):
        """Export API"""
        # Uses Basic Auth

    def read_user_profile(self, user_id: str):
        """User Profile API"""
        # Uses Api-Key auth

    def write_events(self, events: List[Dict]):
        """HTTP V2 API"""
        # Uses body-based api_key

    def batch_upload_events(self, events: List[Dict]):
        """Batch Upload API"""
        # Uses body-based api_key, larger payloads

    def update_user_properties(self, user_id: str, properties: Dict):
        """Identify API"""
        # Uses body-based api_key
```

### Option 2: Separate Driver Classes

```python
class AmplitudeExportDriver(BaseDriver):
    """Export & User Profile APIs (read-only)"""
    # Basic Auth for export
    # Api-Key auth for profile

class AmplitudeIngestDriver(BaseDriver):
    """HTTP V2, Batch, Identify APIs (write-only)"""
    # Body-based api_key for all
```

### Critical Implementation Details

1. **Authentication Matrix:** Create endpoint-specific auth logic
2. **Per-Request Headers:** Never set Content-Type in session headers
3. **ZIP Handling:** Export API returns zipped archive
4. **Response Wrapping:** User Profile wraps response in `userData` object
5. **Rate Limit Handling:** Different limits per API
6. **Region Support:** Allow configurable region (standard vs EU)

---

## JSON Schema Reference

See `AMPLITUDE_API_ANALYSIS.json` for complete structured analysis including:
- Exact curl examples
- Complete response structures
- All query parameters
- All HTTP status codes
- Complete rate limit details

---

## Next Steps

1. ✅ **Analysis Complete** - All APIs documented
2. **Next:** Generate driver implementation following these critical findings
3. **Validation:** Test each authentication method independently
4. **Documentation:** Create README with API-specific examples

