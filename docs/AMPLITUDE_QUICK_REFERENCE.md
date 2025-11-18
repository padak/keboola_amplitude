# Amplitude APIs - Quick Reference Card

## 5 APIs at a Glance

### 1. HTTP V2 API (Write)
- **URL:** `https://api2.amplitude.com/2/httpapi` (or `.eu.amplitude.com`)
- **Method:** POST
- **Auth:** `api_key` in JSON body
- **Max Payload:** 1 MB
- **Max Events:** 2,000 per request
- **Response:** `{events_ingested, payload_size_bytes, server_upload_time}`

```bash
curl -X POST https://api2.amplitude.com/2/httpapi \
  -H 'Content-Type: application/json' \
  -d '{"api_key":"KEY","events":[{"user_id":"123","event_type":"click","time":1234567890000}]}'
```

---

### 2. Batch Event Upload API (Write - Bulk)
- **URL:** `https://api2.amplitude.com/batch` (or `.eu.amplitude.com`)
- **Method:** POST
- **Auth:** `api_key` in JSON body
- **Max Payload:** 20 MB ⬅️ BIGGER than HTTP V2
- **Max Events:** 2,000 per request
- **Response:** `{code, events_ingested, payload_size_bytes, server_upload_time}`

```bash
curl -X POST https://api2.amplitude.com/batch \
  -H 'Content-Type: application/json' \
  -d '{"api_key":"KEY","events":[...]}'
```

---

### 3. Identify API (Update)
- **URL:** `https://api2.amplitude.com/identify` (or `.eu.amplitude.com`)
- **Method:** POST
- **Auth:** `api_key` in form-encoded body
- **Content-Type:** `application/x-www-form-urlencoded` ⬅️ NOT JSON
- **Rate Limit:** 1,800 property updates/hour/user
- **Response:** Status code only (200 = success)

```bash
curl -X POST https://api2.amplitude.com/identify \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'api_key=KEY&identification=[{"user_id":"123","user_properties":{"prop":"value"}}]'
```

---

### 4. Export API (Read)
- **URL:** `https://amplitude.com/api/2/export` (or `.eu.analytics.amplitude.com`)
- **Method:** GET
- **Auth:** Basic Auth - `Authorization: Basic base64(api_key:secret_key)` ⬅️ TWO SECRETS
- **Query Params:** `start=YYYYMMDDTHH&end=YYYYMMDDTHH`
- **Response:** **Zipped archive** of JSON files
- **Max Size:** 4 GB

```bash
curl -X GET 'https://amplitude.com/api/2/export?start=20220201T05&end=20220205T23' \
  -u 'api_key:secret_key'

# OR explicitly:
curl -X GET 'https://amplitude.com/api/2/export?start=20220201T05&end=20220205T23' \
  -H 'Authorization: Basic BASE64_ENCODED_CREDENTIALS'
```

**Time Format:** `YYYYMMDDTHH` (Year-Month-Day T Hour)
- ✅ `20220201T05` = Feb 1, 2022 at 5 AM
- ❌ `2022-02-01` = WRONG format

---

### 5. User Profile API (Read)
- **URL:** `https://profile-api.amplitude.com/v1/userprofile`
- **Method:** GET
- **Auth:** `Authorization: Api-Key secret_key` ⬅️ "Api-Key" prefix (NOT "Bearer")
- **Query Params:** `user_id=X` or `device_id=X` (at least one required)
- **Rate Limit:** 600 requests/minute
- **Response:** Wrapped in `userData` object

```bash
curl -X GET 'https://profile-api.amplitude.com/v1/userprofile?user_id=12345&get_recs=true' \
  -H 'Authorization: Api-Key SECRET_KEY'
```

**Optional params:**
- `get_recs=true` - Include recommendations
- `get_amp_props=true` - Include Amplitude properties
- `get_cohort_ids=true` - Include cohort membership
- `get_propensity=true` - Include propensity predictions

---

## Authentication Quick Reference

| API | Header Name | Format | Example |
|-----|-------------|--------|---------|
| HTTP V2 | ❌ None | Body: `"api_key":"KEY"` | `{"api_key":"abc123",...}` |
| Batch | ❌ None | Body: `"api_key":"KEY"` | `{"api_key":"abc123",...}` |
| Identify | ❌ None | Body: `api_key=KEY` | `api_key=abc123&identification=[...]` |
| Export | ✅ Authorization | `Basic base64(KEY:SECRET)` | `-u 'key:secret'` |
| User Profile | ✅ Authorization | `Api-Key SECRET` | `-H 'Authorization: Api-Key xyz'` |

---

## Content-Type Quick Reference

| API | Method | Content-Type | How Set |
|-----|--------|--------------|---------|
| HTTP V2 | POST | `application/json` | Use `json=data` parameter |
| Batch | POST | `application/json` | Use `json=data` parameter |
| Identify | POST | `application/x-www-form-urlencoded` | Use `data=form_data` parameter |
| Export | GET | None | N/A (no body) |
| User Profile | GET | None | N/A (no body) |

---

## Rate Limits Quick Reference

| API | Limit | Value |
|-----|-------|-------|
| HTTP V2 | Payload | 1 MB |
| HTTP V2 | Events/request | 2,000 |
| Batch | Payload | **20 MB** |
| Batch | Events/request | 2,000 |
| Batch | Daily quota | 500K per device/user |
| Identify | Property updates/hour/user | 1,800 |
| Export | Export size | 4 GB |
| User Profile | Requests/minute | 600 |

---

## Response Field Names (Exact Case!)

### Write APIs (HTTP V2, Batch)
```json
{
  "code": 200,
  "events_ingested": 123,
  "payload_size_bytes": 4567,
  "server_upload_time": 1639757639123
}
```

### User Profile API (Wrapped!)
```json
{
  "userData": {
    "user_id": "12345",
    "device_id": "abc-def",
    "amp_props": {...},
    "cohort_ids": [...],
    "propensities": [...]
  }
}
```

### Export API
```
[Zipped archive - decompress to get JSON]
```

---

## Regional Endpoints

### Standard (US)
- HTTP V2: `https://api2.amplitude.com/2/httpapi`
- Batch: `https://api2.amplitude.com/batch`
- Identify: `https://api2.amplitude.com/identify`
- Export: `https://amplitude.com/api/2/export`
- User Profile: `https://profile-api.amplitude.com/v1/userprofile`

### EU Residency
- HTTP V2: `https://api.eu.amplitude.com/2/httpapi`
- Batch: `https://api.eu.amplitude.com/batch`
- Identify: `https://api.eu.amplitude.com/identify`
- Export: `https://analytics.eu.amplitude.com/api/2/export`
- User Profile: N/A (US only)

---

## Capabilities Matrix

| Feature | Support | APIs |
|---------|---------|------|
| Read | ✅ | Export, User Profile |
| Write | ✅ | HTTP V2, Batch, Identify |
| Update | ✅ | Identify |
| Delete | ❌ | None |
| Batch | ✅ | HTTP V2 (2K), Batch (2K) |
| Pagination | ❌ | None |

---

## Implementation Checklist

### Authentication
- [ ] HTTP V2: Put `api_key` in JSON body
- [ ] Batch: Put `api_key` in JSON body
- [ ] Identify: Put `api_key` in form-encoded body
- [ ] Export: Create Basic Auth with `api_key:secret_key`
- [ ] User Profile: Set `Authorization: Api-Key secret_key` header

### Content-Type
- [ ] Don't set Content-Type in session headers
- [ ] HTTP V2 POST: Use `json=data` (sets JSON automatically)
- [ ] Batch POST: Use `json=data` (sets JSON automatically)
- [ ] Identify POST: Use `data=form_data` (sets form-encoded automatically)
- [ ] Export GET: No body, no Content-Type
- [ ] User Profile GET: No body, no Content-Type

### Response Parsing
- [ ] Write APIs: Extract `events_ingested` from response
- [ ] User Profile: Extract from `userData` wrapper
- [ ] Export: Decompress ZIP archive
- [ ] Handle all error codes (400, 413, 429, 503, etc.)

### Rate Limiting
- [ ] HTTP V2: Validate payload ≤ 1 MB
- [ ] Batch: Validate payload ≤ 20 MB
- [ ] Batch: Validate events ≤ 2,000
- [ ] Identify: Track property updates (1,800/hour/user)
- [ ] User Profile: Implement 600 req/min throttle
- [ ] All APIs: Implement exponential backoff on 429

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 400 Bad Request | Invalid JSON, missing fields | Check required fields: api_key, events |
| 401 Unauthorized | Wrong credentials | Check api_key and secret_key (for Export) |
| 413 Payload Too Large | Exceeded size limit | Reduce payload (1MB vs 20MB limit) |
| 429 Rate Limited | Too many requests | Implement exponential backoff, retry after X seconds |
| 503 Service Unavailable | API down | Retry with backoff |

---

## Testing Curl Commands

### Test HTTP V2
```bash
curl -X POST https://api2.amplitude.com/2/httpapi \
  -H 'Content-Type: application/json' \
  -d '{"api_key":"YOUR_KEY","events":[{"user_id":"test123","event_type":"test_event","time":1234567890000}]}'
```

### Test Identify
```bash
curl -X POST https://api2.amplitude.com/identify \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'api_key=YOUR_KEY&identification=[{"user_id":"test123","user_properties":{"key":"value"}}]'
```

### Test Export
```bash
curl -X GET 'https://amplitude.com/api/2/export?start=20250101T00&end=20250102T00' \
  -u 'API_KEY:SECRET_KEY' \
  -o export.zip
```

### Test User Profile
```bash
curl -X GET 'https://profile-api.amplitude.com/v1/userprofile?user_id=test123&get_amp_props=true' \
  -H 'Authorization: Api-Key YOUR_SECRET_KEY'
```

---

**Last Updated:** 2025-11-17
**For Full Details:** See `AMPLITUDE_API_ANALYSIS.json`

