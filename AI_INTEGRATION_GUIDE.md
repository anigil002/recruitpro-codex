# RecruitPro AI Integration Guide

## Overview

RecruitPro features a **fully implemented, production-ready AI integration** with Google's Gemini API. This guide explains how the AI integration works, how to enable it, and how the fallback system ensures the application never breaks.

## Architecture

### Core Components

1. **`app/services/gemini.py`** - Main AI service implementation
   - `GeminiService` class: Handles all AI interactions
   - Live API integration with Google Gemini
   - Intelligent fallback system for offline/development mode
   - Model: `gemini-2.5-flash-lite` (default)

2. **`app/services/ai.py`** - AI orchestration layer
   - Background job queue integration
   - Job lifecycle management
   - Real-time event publishing

3. **`app/routers/ai.py`** - API endpoints
   - REST endpoints for all AI features
   - Authentication and authorization
   - Request validation

## AI Features (Fully Implemented)

### 1. CV Screening (`screen_cv()`)
**Location**: `app/services/gemini.py:1088-1288`

Comprehensive CV screening following Egis Middle East & North America standards:
- Full CV analysis (no truncation)
- Structured compliance table
- Evidence-based assessment
- Role matching and recommendations
- Outputs: candidate info, screening summary, compliance table, final recommendation

**Fallback**: Basic candidate extraction (name, email, phone) with manual review recommendation

### 2. Document Analysis (`analyze_file()`)
**Location**: `app/services/gemini.py:395-438`

Analyzes project documents and extracts structured information:
- Project information extraction (name, client, sector, location, scope)
- Position/role identification
- Multiple position detection from tables
- Document type classification (project scope, JD, positions list, mixed)
- Supports PDF, DOCX, CSV, TXT

**Fallback**: Heuristic-based extraction using regex patterns and keyword detection

### 3. Job Description Generation (`generate_job_description()`)
**Location**: `app/services/gemini.py:716-777`

Creates professional job descriptions:
- Based on role title and context
- Includes responsibilities, requirements, nice-to-haves
- Compensation notes
- Project context integration

**Fallback**: Template-based JDs with sensible defaults for AEC/infrastructure roles

### 4. Market Research (`generate_market_research()`)
**Location**: `app/services/gemini.py:948-997`

Generates market intelligence:
- Regional market insights
- Sector-specific findings
- Talent availability analysis
- Comparable projects
- Source citations

**Fallback**: Generic market insights based on region and sector keywords

### 5. Salary Benchmarking (`generate_salary_benchmark()`)
**Location**: `app/services/gemini.py:999-1040`

Provides compensation data:
- Currency-specific ranges (min/mid/max)
- Seniority adjustments
- Role and region factors
- Rationale and sources

**Fallback**: Formula-based calculation using role, seniority, and region parameters

### 6. Candidate Scoring (`score_candidate()`)
**Location**: `app/services/gemini.py:1042-1086`

Evaluates candidates against positions:
- Technical fit score
- Cultural alignment score
- Growth potential score
- Overall match score
- Detailed notes

**Fallback**: Skills and experience-based scoring algorithm

### 7. Outreach Generation (`generate_outreach_email()`)
**Location**: `app/services/gemini.py:779-834`

Creates personalized outreach emails:
- Multiple templates (standard, executive, technical)
- Candidate personalization
- Role highlights
- Company branding

**Fallback**: Template-based emails with variable substitution

### 8. Call Script Generation (`generate_call_script()`)
**Location**: `app/services/gemini.py:836-908`

Structured call scripts for recruiters:
- Introduction and context
- Motivation probing questions
- Technical/managerial/commercial questions
- Objection handling
- Closing

**Fallback**: Comprehensive default script with question banks

### 9. Chatbot Assistant (`generate_chatbot_reply()`)
**Location**: `app/services/gemini.py:910-943`

Conversational AI assistant:
- Context-aware responses
- Tool suggestions (market research, sourcing, benchmarking)
- Session history tracking
- Multi-turn conversations

**Fallback**: Intent-based responses using keyword detection

### 10. Boolean Search Generation (`build_boolean_search()`)
**Location**: `app/services/gemini.py:1290-1296`

LinkedIn X-Ray search strings:
- Based on candidate persona
- Skills, title, location, seniority
- Optimized for Google CSE

**Fallback**: Rule-based boolean string construction

### 11. Candidate Profile Synthesis (`synthesise_candidate_profiles()`)
**Location**: `app/services/gemini.py:1298-1311`

Generates sample candidate profiles:
- Based on persona and requirements
- Quality scores
- Profile summaries

**Fallback**: Template-based profile generation

## How to Enable Real AI Integration

### Step 1: Get a Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### Step 2: Configure RecruitPro

Edit the `.env` file in the project root:

```bash
# Uncomment and set your API key
RECRUITPRO_GEMINI_API_KEY=your-actual-api-key-here
```

### Step 3: Restart the Application

```bash
# Stop the current server (Ctrl+C)
# Restart
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 4: Verify Integration

Check the logs on startup - you should see Gemini initialization messages.

Test an AI endpoint:

```bash
curl -X POST http://localhost:8000/api/ai/generate-jd \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"title": "Senior Project Manager"}'
```

## Understanding Fallback Mode

### What is Fallback Mode?

RecruitPro's AI integration includes an **intelligent fallback system** that activates when:
1. No Gemini API key is configured
2. Network connectivity issues prevent API calls
3. API quota limits are exceeded
4. API returns errors

### How Fallbacks Work

Each AI function has a corresponding `fallback()` function that provides:
- **Deterministic responses** (same input → same output)
- **Sensible defaults** based on industry best practices
- **Rule-based logic** using heuristics and templates
- **Valid data structures** matching the expected schema

### Example: CV Screening Fallback

When the Gemini API is unavailable, the CV screening fallback:
1. Extracts candidate name from first few lines (heuristic)
2. Uses regex to find email and phone
3. Returns a "manual review needed" recommendation
4. Includes appropriate tags for follow-up

This ensures the system **never crashes** - it gracefully degrades while maintaining functionality.

### Identifying Fallback Mode

**In fallback mode, you'll notice:**
- Generic, template-based responses
- Shorter, less detailed analyses
- Consistent phrasing across similar requests
- Tags like `["fallback_screening", "manual_review_needed"]`

**With live AI enabled, you'll see:**
- Detailed, context-specific analyses
- Unique responses for each request
- Evidence-based reasoning
- Comprehensive compliance tables

## Performance Considerations

### API Costs

Gemini API pricing (as of 2024):
- **gemini-2.5-flash-lite**: Very low cost per token
- Typical CV screening: ~$0.001-0.01 per request
- Typical JD generation: ~$0.0005-0.005 per request

**Budget recommendation**: Start with $10-20/month for testing, scale based on usage.

### Rate Limits

Default Gemini API limits:
- 60 requests per minute
- 1,500 requests per day (free tier)

RecruitPro includes retry logic and queue management to handle rate limits gracefully.

### Response Times

Typical latencies:
- CV Screening: 2-5 seconds
- Document Analysis: 1-3 seconds
- JD Generation: 1-2 seconds
- Simple queries (scoring, boolean search): <1 second

Fallback mode: **Instant** (no network calls)

## Testing AI Integration

### Unit Tests

Run the AI integration test suite:

```bash
pytest tests/test_ai_integrations.py -v
```

This verifies:
- Gemini model selection
- Background queue handlers
- Fallback behavior

### Integration Tests

Test full end-to-end flows:

```bash
pytest tests/test_gemini_parsing.py -v
```

### Manual Testing

Use the Swagger UI at `http://localhost:8000/docs` to test endpoints:
1. `/api/ai/screen-candidate`
2. `/api/ai/generate-jd`
3. `/api/ai/source-candidates`
4. `/api/research/salary-benchmark`

## Advanced Configuration

### Changing the Model

Edit `app/services/gemini.py:65`:

```python
DEFAULT_MODEL = "gemini-2.5-flash-lite"  # Change to another model
```

Available models:
- `gemini-2.5-flash-lite` (fastest, cheapest, recommended)
- `gemini-2.0-flash` (balanced)
- `gemini-1.5-pro` (most capable, higher cost)

### Adjusting Temperature

Lower temperature = more deterministic responses
Higher temperature = more creative responses

Edit `app/services/gemini.py:68`:

```python
def __init__(self, model: str = DEFAULT_MODEL, temperature: float = 0.15):
```

**Recommendation**: Keep at 0.15 for recruitment use cases (consistent, professional output)

### Custom Prompts

All prompts are defined in the respective functions in `app/services/gemini.py`.

For example, to customize CV screening prompts, edit the `screen_cv()` function starting at line 1088.

## Monitoring and Logging

### Enable Debug Logging

Add to `.env`:

```bash
RECRUITPRO_LOG_LEVEL=DEBUG
```

### View Gemini API Calls

Logs include:
- Request timestamps
- Token usage
- Response times
- Fallback activation events
- Error details

### Job Status Tracking

All AI jobs are tracked in the database:

```python
from app.models import AIJob
# Query recent jobs
jobs = session.query(AIJob).order_by(AIJob.created_at.desc()).limit(10).all()
for job in jobs:
    print(f"{job.job_type}: {job.status}")
```

## Troubleshooting

### Issue: "Gemini API key is not configured"

**Solution**: Set `RECRUITPRO_GEMINI_API_KEY` in `.env`

### Issue: "Gemini HTTP request failed"

**Possible causes**:
1. Invalid API key
2. Network connectivity issues
3. API quota exceeded

**Solution**: Check logs for detailed error, verify API key, check quota at [Google AI Studio](https://aistudio.google.com)

### Issue: Responses seem generic

**Likely cause**: Running in fallback mode (no API key set)

**Solution**: Configure Gemini API key as described above

### Issue: Slow responses

**Possible causes**:
1. Large document processing
2. Network latency
3. API rate limiting

**Solutions**:
- Use background jobs for large documents
- Check network connection
- Verify API quota

## Migration from Fallback to Live AI

If you've been running in fallback mode and want to migrate to live AI:

1. **No data migration needed** - fallback responses are stored the same way as AI responses
2. **Set API key** in `.env`
3. **Restart application**
4. **New requests will use live AI** automatically
5. **Old data remains unchanged** (no need to reprocess)

## Security Considerations

### API Key Protection

- **Never commit** `.env` file to version control
- `.env` is in `.gitignore` by default
- Use environment variables in production
- Rotate keys periodically

### Data Privacy

- **No data retention by Gemini**: Google's API terms specify they don't use your data for model training
- **Local processing**: All CV and document data is processed locally before API calls
- **Secure transmission**: HTTPS only

### Compliance

For GDPR/data protection compliance:
- Document that CV data is sent to Google Gemini API
- Include in privacy policy
- Obtain candidate consent if required
- Consider using fallback mode for sensitive data

## Production Deployment

### Recommended Setup

1. **Use environment variables** (not `.env` file)
2. **Set API key via secrets manager** (AWS Secrets Manager, Azure Key Vault, etc.)
3. **Monitor API usage and costs**
4. **Set up logging and alerting**
5. **Configure rate limiting** at application level
6. **Enable background job processing** for long-running tasks

### Example: AWS Deployment

```bash
# Set environment variable in AWS ECS/Fargate
RECRUITPRO_GEMINI_API_KEY: !Ref GeminiApiKeySecret

# In Secrets Manager
aws secretsmanager create-secret \
  --name recruitpro/gemini-api-key \
  --secret-string "your-api-key"
```

## FAQ

**Q: Is the AI integration real or fake?**
A: **Real**. The implementation includes full Gemini API integration with intelligent fallbacks.

**Q: Why do responses seem generic?**
A: You're likely running in fallback mode. Set `RECRUITPRO_GEMINI_API_KEY` to enable live AI.

**Q: Can I use a different AI provider?**
A: Yes. The `GeminiService` class can be extended or replaced. You'd need to implement the same method signatures.

**Q: How much does it cost to run?**
A: Very low. With `gemini-2.5-flash-lite`, expect $0.001-0.01 per CV screening. For 100 CVs/day, ~$10-30/month.

**Q: Is my data secure?**
A: Yes. Transmission is HTTPS-only, and Google doesn't use your data for training per API terms.

**Q: Can I run completely offline?**
A: Yes. Fallback mode requires no internet and provides functional (though less sophisticated) responses.

**Q: How do I know if AI is working?**
A: Check logs for "Gemini" messages, or test an endpoint and look for detailed, context-specific responses.

## Support

For issues or questions:
1. Check logs at startup for Gemini initialization
2. Review this guide and troubleshooting section
3. Test with Swagger UI at `/docs`
4. Open an issue on GitHub with logs and error details

## Summary

| Feature | Status | Location | Fallback |
|---------|--------|----------|----------|
| CV Screening | ✅ Implemented | `gemini.py:1088` | ✅ Heuristic extraction |
| Document Analysis | ✅ Implemented | `gemini.py:395` | ✅ Regex patterns |
| JD Generation | ✅ Implemented | `gemini.py:716` | ✅ Templates |
| Market Research | ✅ Implemented | `gemini.py:948` | ✅ Generic insights |
| Salary Benchmarking | ✅ Implemented | `gemini.py:999` | ✅ Formula-based |
| Candidate Scoring | ✅ Implemented | `gemini.py:1042` | ✅ Algorithm |
| Outreach Generation | ✅ Implemented | `gemini.py:779` | ✅ Templates |
| Call Scripts | ✅ Implemented | `gemini.py:836` | ✅ Default script |
| Chatbot | ✅ Implemented | `gemini.py:910` | ✅ Intent-based |
| Boolean Search | ✅ Implemented | `gemini.py:1290` | ✅ Rule-based |

**Configuration required**: Set `RECRUITPRO_GEMINI_API_KEY` in `.env` to enable live AI integration.
