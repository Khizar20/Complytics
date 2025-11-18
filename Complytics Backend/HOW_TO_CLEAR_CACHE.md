# How to Clear Compliance Chatbot Cache

## Overview

The compliance chatbot caches responses to improve performance. If you want to force fresh answers (e.g., after updating framework documents or testing the evidence-based approach), you can clear the cache.

## 🔄 Caching System

### What Gets Cached:
1. **Exact Query Responses** - Same question = Same cached answer
2. **Expert Responses** - Individual expert outputs
3. **Gemini API Calls** - LLM responses
4. **Compliance Classifications** - Query classification results

### Cache Storage:
- **In-Memory**: `QUERY_CACHE` dictionary
- **On-Disk**: `compliance_cache/query_cache.json`

---

## 🗑️ Method 1: Via API Endpoint (Recommended)

### Clear Cache for Your Session:

```bash
curl -X POST http://localhost:8000/api/compliance/clear-cache \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "message": "Query cache cleared successfully",
  "cache_entries_cleared": 156,
  "status": "success"
}
```

### From Frontend (JavaScript):

```javascript
const clearCache = async () => {
  const response = await fetch('/api/compliance/clear-cache', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  const result = await response.json();
  console.log(result.message);
};
```

---

## 🗑️ Method 2: Using Python Script

Run the included script:

```bash
cd "Complytics Backend"
python clear_cache.py
```

---

## 🗑️ Method 3: Manual File Deletion

1. Stop the backend server
2. Delete cache files:
   ```bash
   cd "Complytics Backend"
   rm -f compliance_cache/query_cache.json
   rm -f compliance_cache/classification_feedback.json
   ```
3. Restart the backend server

---

## 🔍 When to Clear Cache:

### **Always Clear After:**
- ✅ Updating framework PDF documents
- ✅ Regenerating embeddings
- ✅ Fixing expert prompts
- ✅ Testing evidence-based citations

### **Optional Clear When:**
- Testing same query with different context
- Verifying prompt improvements
- Debugging response quality

---

## ⚠️ Important Notes:

1. **Caching Logic Remains**: The system will start caching again immediately
2. **Performance Impact**: First queries after clearing will be slower
3. **No Data Loss**: Only cached responses are cleared, not conversation history or embeddings
4. **User-Specific**: Clearing cache doesn't affect other users

---

## 🧪 Testing Evidence-Based Approach:

After clearing cache, test with these queries to verify framework citations:

1. **GDPR**: "What are the GDPR data breach notification requirements?"
2. **HIPAA**: "What technical safeguards does HIPAA require?"
3. **ISO 27001**: "What are ISO 27001 certification audit requirements?"

Check logs for:
- ✅ Segments retrieved > 0
- ✅ Context length > 0 characters
- ✅ Response includes citations like `(⚖️ Legal Basis: "exact quote" - Article X)`

---

## 📊 Cache Statistics:

To see cache size without clearing:

```python
from compliance_rag import QUERY_CACHE
print(f"Current cache entries: {len(QUERY_CACHE)}")
```

---

## 🚀 Quick Clear & Test:

```bash
# 1. Clear cache
python clear_cache.py

# 2. Restart server
uvicorn app:app --reload

# 3. Test query
curl -X POST http://localhost:8000/api/compliance/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "What are GDPR breach notification requirements?"}'
```

