# Azure Checker Module - Roman Urdu Documentation

## Module Ka Naam
**Azure Checker Module** - Ye module Azure cloud configurations aur documents ko analyze karta hai aur unhein compliance frameworks (Azure Best Practices, GDPR, ISO 27001, ISO 27017, ISO 27018) ke against check karta hai.

## Module Ka Kaam Kya Hai?

Ye module:
- Azure configuration documents ko upload karne ki facility deta hai
- Documents ko multiple compliance frameworks ke against analyze karta hai
- Detailed compliance reports generate karta hai (PDF format mein)
- Non-compliance issues identify karta hai
- Recommendations provide karta hai
- Compliance scores calculate karta hai

## Flow Kaise Kaam Karta Hai?

### 1. Document Upload
- User document upload karta hai (PDF, DOCX, TXT, JSON formats)
- System file ko validate karta hai:
  - File size check (max 50MB)
  - File type check
  - Image files ko reject karta hai
  - Document relevance check karta hai (Azure/cloud related hai ya nahi)

### 2. Text Extraction
- Document se text extract hota hai
- Text ko clean aur chunk mein divide kiya jata hai
- Chunks ko process kiya jata hai embedding ke liye

### 3. Framework Selection
- User framework select karta hai:
  - Azure Best Practices
  - GDPR
  - ISO 27001
  - ISO 27017
  - ISO 27018
- Multiple frameworks bhi select kiye ja sakte hain

### 4. Embedding & Similarity Search
- Document chunks ka embedding create hota hai
- Framework-specific embeddings se similarity search hoti hai
- Relevant compliance requirements identify hote hain

### 5. Compliance Analysis
- Document content ko compliance requirements se compare kiya jata hai
- Non-compliance issues detect hote hain
- Compliance scores calculate hote hain
- Category-wise analysis hoti hai:
  - Security
  - Identity
  - Storage
  - Networking
  - Monitoring
  - Compliance

### 6. Report Generation
- Detailed PDF report generate hoti hai
- Report mein include hota hai:
  - Executive summary
  - Compliance scores
  - Category-wise findings
  - Non-compliance issues
  - Recommendations
  - Compliance checklist

### 7. Report Download
- Generated report ko user download kar sakta hai
- Reports `azure_checker/reports/` folder mein store hote hain

## Technical Working

### Embedding Engine
1. **Framework-Specific Embeddings**: Har framework ka apna embedding engine hota hai
2. **Document Embeddings**: Uploaded document ka embedding create hota hai
3. **Similarity Search**: FAISS index use karke similarity search hoti hai
4. **Relevant Chunks**: Most relevant compliance chunks retrieve hote hain

### Compliance Analyzer
1. **Category Detection**: Document content ko categories mein classify karta hai
2. **Requirement Matching**: Compliance requirements se match karta hai
3. **Gap Analysis**: Missing requirements identify karta hai
4. **Score Calculation**: Compliance score calculate karta hai

### Report Generator
1. **PDF Creation**: ReportLab library use karke PDF create hoti hai
2. **Formatting**: Professional formatting apply hoti hai
3. **Tables**: Compliance tables generate hote hain
4. **Charts**: Visual representations add hote hain

### Compliance Scores Kaise Generate Hote Hain?
- **Similarity Se Score**: `AzureComplianceAnalyzer.analyze_document()` FAISS search se top chunks leta hai, har category (Security, Identity, Storage, Networking, Monitoring, Compliance, Governance, etc.) ka average similarity calculate karta hai. Ye similarity 0-1 range se 0-100 percent mein convert hoti hai (e.g. 0.82 → 82%).
- **AI Validation**: Har category ke top 3 best-practice chunks + uploaded document ka text Gemini ko diya jata hai (`_analyze_category_with_ai`). AI se status (Compliant/Partial/Non-Compliant), gaps aur recommendations milte hain. Agar AI fail ho to fallback `determine_compliance_status()` similarity thresholds (>=0.80 Compliant, >=0.60 Partial, otherwise Non-Compliant) apply karta hai.
- **Category Aggregation**: Category-wise findings ko sort karke severity highlight ki jaati hai aur har category ka confidence `similarity * 100` ke form mein store hota hai. Ye direct UI mein Key Findings cards mein use hota hai.
- **Framework Scores**: Har selected framework (GDPR, ISO 27001, ISO 27017, ISO 27018, Azure Best Practices) ke liye upar wala process independently run hota hai. `framework_scores` map store karta hai `{framework_name: score}` jis se grid + bar chart render hota hai.
- **Overall Score**: `_perform_compliance_analysis()` sab frameworks ke scores ka average leta hai. >=80 ho to `Compliant`, 60-79 `Partial`, aur <60 `Non-Compliant`. Ye overall score gauge, executive summary aur PDF report mein re-use hota hai.
- **Evidence Trail**: Har score ke saath findings, AI key points aur FAISS matched chunks persist hote hain taake user ko pata rahe ke kis requirement ne kitna score dila ya deduct kiya.

## Files Jahan Code Present Hai

### Backend Files (Python)

1. **`Complytics Backend/routes/azure_checker.py`**
   - Main API routes file
   - `/api/azure-checker/upload` endpoint
   - `/api/azure-checker/analyze` endpoint
   - `/api/azure-checker/report` endpoint
   - File validation logic
   - Report generation logic
   - PDF creation functions

2. **`Complytics Backend/azure_checker/utils/text_extraction.py`**
   - Text extraction from PDF
   - Text extraction from DOCX
   - Text cleaning functions
   - Text chunking functions

3. **`Complytics Backend/azure_checker/utils/embedding_engine.py`**
   - Embedding engine class
   - Framework-specific embedding loading
   - Similarity search functions
   - Document embedding creation

4. **`Complytics Backend/azure_checker/utils/compliance_logic.py`**
   - AzureComplianceAnalyzer class
   - Compliance categories definition
   - Requirement matching logic
   - Score calculation functions
   - Gap analysis functions

5. **`Complytics Backend/azure_checker/create_azure_embeddings.py`**
   - Azure documents se embeddings create karta hai
   - FAISS index build karta hai
   - Document map create karta hai

6. **`Complytics Backend/azure_checker/create_all_framework_embeddings.py`**
   - Sab frameworks ke embeddings create karta hai
   - Batch processing

7. **`Complytics Backend/azure_checker/__init__.py`**
   - Module initialization

### Frontend Files (React/JSX)

1. **`src/components/team/AzureComplianceChecker.jsx`**
   - Main UI component
   - File upload interface
   - Framework selection UI
   - Report display
   - Download functionality

2. **`src/lib/api.js`**
   - API utility functions

### Data Files

1. **`Complytics Backend/azure_checker/azure_docs/`**
   - Azure documentation PDFs
   - Source documents for Azure framework

2. **`Complytics Backend/azure_checker/compliance_docs/`**
   - Compliance framework PDFs (GDPR, ISO 27001, etc.)

3. **`Complytics Backend/azure_checker/embeddings/`**
   - `azure/azure_embeddings.npy` - Azure embeddings
   - `azure/azure_document_map.json` - Azure document map
   - `gdpr/gdpr_embeddings.npy` - GDPR embeddings
   - `iso27001/iso27001_embeddings.npy` - ISO 27001 embeddings
   - `iso27017/` - ISO 27017 embeddings
   - `iso27018/iso27018_embeddings.npy` - ISO 27018 embeddings

4. **`Complytics Backend/azure_checker/faiss_indexes/`**
   - `azure/azure_index.faiss` - Azure FAISS index
   - `gdpr/gdpr_index.faiss` - GDPR FAISS index
   - `iso27001/iso27001_index.faiss` - ISO 27001 FAISS index
   - `iso27018/iso27018_index.faiss` - ISO 27018 FAISS index

5. **`Complytics Backend/azure_checker/reports/`**
   - Generated PDF reports
   - Timestamped report files

## Key Functions

### Main Functions in `azure_checker.py`:
- `load_framework_engine()` - Framework engine loading
- `validate_document_relevance()` - Document relevance validation
- `generate_compliance_report()` - PDF report generation
- `analyze_document()` - Document analysis

### Main Functions in `text_extraction.py`:
- `extract_text_from_file()` - File se text extraction
- `clean_text()` - Text cleaning
- `chunk_text()` - Text chunking

### Main Functions in `embedding_engine.py`:
- `AzureEmbeddingEngine` class - Embedding engine
- `create_embedding()` - Embedding creation
- `search_similar()` - Similarity search

### Main Functions in `compliance_logic.py`:
- `AzureComplianceAnalyzer` class - Compliance analyzer
- `analyze_document()` - Document analysis
- `calculate_compliance_score()` - Score calculation
- `identify_gaps()` - Gap identification

## API Endpoints

- `POST /api/azure-checker/upload` - Document upload endpoint
- `POST /api/azure-checker/analyze` - Document analysis endpoint
- `GET /api/azure-checker/report/{report_id}` - Report download endpoint

## Supported File Formats

- PDF (`.pdf`)
- Word Document (`.docx`, `.doc`)
- Text File (`.txt`)
- JSON (`.json`)

## Supported Frameworks

1. **Azure Best Practices** - Azure cloud best practices
2. **GDPR** - General Data Protection Regulation
3. **ISO 27001** - Information Security Management
4. **ISO 27017** - Cloud Security
5. **ISO 27018** - Cloud Privacy

## Compliance Categories

1. **Security** - Encryption, SSL/TLS, Firewall, Authentication, etc.
2. **Identity** - Azure AD, Active Directory, SSO, etc.
3. **Storage** - Storage accounts, Blob, Encryption, etc.
4. **Networking** - Virtual Network, VPN, Load Balancer, etc.
5. **Monitoring** - Logging, Alerts, Metrics, etc.
6. **Compliance** - Regulatory compliance requirements

## Dependencies

- **FastAPI** - Web framework
- **ReportLab** - PDF generation
- **SentenceTransformer** - Embedding model
- **FAISS** - Vector similarity search
- **PyPDF2/pdfplumber** - PDF processing
- **python-docx** - DOCX processing
- **Google Gemini AI** - AI analysis

## Summary

Ye module Azure configurations ko compliance frameworks ke against check karta hai:
- Documents upload karne ki facility
- Multiple frameworks support
- Detailed analysis aur scoring
- Professional PDF reports
- Recommendations provide karta hai

Sab kuch embedding-based similarity search aur AI analysis ke combination se kaam karta hai.

---

## Story Time: Compliance Team Member Is Module Ko Kaise Use Karta Hai?

Chaliye ek kahani ki soorat mein samajhte hain. Imagine karein ke Ayesha ek compliance engineer hai jo ek fintech company ke Azure environment ko secure rakhne ki zimmedar hai. Company ka CEO usay kehta hai: “Ayesha, humein jaldi se batayein ke hamari Azure architecture GDPR, ISO 27001 aur Azure Best Practices ke mutabiq hai ya nahi. Agle hafta external audit hai.”

Ayesha ka workflow kuch yoon hota hai:

1. **Document Tayyari**  
   - Wo apne DevOps team se recently updated Azure Architecture Deck (PDF), Security Runbook (DOCX) aur Azure Policy Export (JSON) le leti hai.  
   - Ye documents aksar contain karte hain:  
     * Virtual Network diagrams  
     * Access control matrices (Azure AD groups, RBAC roles)  
     * Storage encryption settings  
     * Monitoring aur logging configurations  

2. **Azure Checker Module Khulna**  
   - Superadmin dashboard se “Azure Compliance Checker” section open karti hai.  
   - Frameworks select karti hai: `Azure Best Practices + GDPR + ISO 27001`.

3. **Document Upload Scene**  
   - Ayesha ek hi baar mein teen files upload karti hai (PDF, DOCX, JSON).  
   - Module pehle relevance check karta hai (agar kisi file mein “recipes” ya “marketing copy” ho to reject).  
   - Har file ka text extract hota hai aur chunk-by-chunk embeddings create hoti hain.

4. **Analysis & Wait Moment**  
   - Ayesha coffee sip karte hue wait karti hai jab tak module FAISS similarity search se har framework ka relevant control identify kare.  
   - AI analyzer har category (Security, Identity, Storage, Networking, Monitoring, Compliance) ka compliance score calculate karta hai.

5. **Result & Report**  
   - Dashboard par ek interactive summary aati hai: “Security: 78%, Identity: 92%, Storage: 65%...”  
   - Issues list hoti hain, jaise: “Blob storage encryption missing customer-managed keys (ISO 27018)”  
   - Ayesha “Download PDF” button dabati hai aur ek polished report milti hai jisme executive summary, findings, recommendations sab hota hai.

6. **Follow-up Action**  
   - Wo PDF ko DevOps lead aur CEO ko bhej deti hai.  
   - Next sprint ke liye remediation tickets create ho jati hain.  

**In Short:** Ayesha ko kisi manual checklist ya Excel sheet ki zarurat nahi parti. Bas relevant Azure documents upload karo aur module AI + embeddings se instant compliance insight de deta hai. Audit ke waqt wo confidently bolti hai: “Hamare paas latest Azure compliance report ready hai—ye dekhein evidence!”

