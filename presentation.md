# Complytics Platform - Complete Presentation
## Roman Urdu Mein Layman Language

---

## Story Time: Ek Company Ki Compliance Journey

### Characters:
- **Ayesha** - Compliance Officer (Compliance Team)
- **Farhan** - IT Security Engineer (IT Team)
- **Ahmed** - DevOps Engineer (IT Team)
- **Sara** - CTO/Management (Management Team)
- **TechCorp** - Ek fintech startup jo multiple compliance frameworks follow karna chahti hai

---

### Scene 1: Problem Statement

**TechCorp** ek growing fintech startup hai jo Europe mein customers ko financial services provide karti hai. Company ko multiple challenges face kar rahe hain:

**Ayesha (Compliance Officer) ki Problem:**
- CEO ne kaha: "Ayesha, humein agle quarter mein SOC 2 Type II certification chahiye. Timeline tight hai."
- Ayesha ko manually research karna pad raha hai - GDPR, ISO 27001, SOC 2 ke requirements ko samajhna
- Documents ko manually review karna pad raha hai - privacy policies, security policies
- External consultants expensive hain aur time-consuming hai
- Har framework ke requirements ko track karna mushkil hai

**Farhan (IT Security Engineer) ki Problem:**
- Website ko accessibility aur security ke liye test karna hai
- Manual testing bahut time-consuming hai
- WCAG violations manually find karna mushkil hai
- Security headers check karna pad raha hai
- Authenticated pages ko test karna complicated hai (login ke baad wale pages)

**Ahmed (DevOps Engineer) ki Problem:**
- Azure cloud configurations ko compliance frameworks ke against verify karna hai
- Azure architecture documents ko manually review karna pad raha hai
- Compliance gaps identify karna mushkil hai
- Reports generate karna time-consuming hai

**Sara (CTO) ki Problem:**
- Team activities ko track karna chahti hai
- Compliance status ko monitor karna hai
- Reports aur analytics dekhna hai
- Team productivity ko measure karna hai

---

### Scene 2: Complytics Platform Discovery

Ek din Sara ne ek compliance management platform ke baare mein suna - **Complytics**. Usne team ko bataya aur sab ne decide kiya ke trial karte hain.

**Sara:** "Chaliye dekhte hain ke ye platform hamari problems solve kar sakta hai ya nahi."

---

### Scene 3: Compliance Chatbot Module - Ayesha Ka Experience

**Ayesha ka First Day:**

Ayesha ne Compliance Chatbot module open kiya aur pehla question pucha:

**Ayesha:** "What is SOC 2 Type II certification?"

**Chatbot Response:**
- Detailed explanation mila SOC 2 ke baare mein
- Type I vs Type II ka difference clearly explain hua
- Trust Service Criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy) explain kiye
- Har control ID green highlight mein tha (jaise <span style="color:#008000">SOC 2 CC6.1</span>)

**Ayesha:** "Wow! Ye to bahut detailed aur accurate hai. Ab main comparison kar leti hoon."

**Ayesha:** "What's the difference between SOC 2 and ISO 27001?"

**Chatbot Response:**
- Comparison table mila
- Scope, focus areas, certification process, validity period - sab clearly explain hua
- Evidence-based answers milte hain - har point ke saath exact control IDs cite huye

**Ayesha:** "Perfect! Ab implementation guidance chahiye."

**Ayesha:** "How should we achieve SOC 2 Type II certification? Guide us step by step."

**Chatbot Response:**
- Structured 8-step implementation plan mila
- Har step mein specific controls cite huye
- AWS/Azure specific recommendations mili
- Actionable guidance mili

**Ayesha:** "Ye to bahut helpful hai! Ab main apni existing privacy policy ko check kar leti hoon."

Ayesha ne apni company ki privacy policy document upload kiya aur chatbot se pucha:

**Ayesha:** "Check if my document covers GDPR requirements."

**Chatbot Response:**
- Document analyze hua
- ✅ Covered requirements (with evidence)
- ❌ Missing requirements (with specific article numbers)
- 📝 Improvement suggestions (actionable recommendations)

**Ayesha:** "Perfect! Ab mujhe clearly pata hai ke kya add karna hai. Ye chatbot to meri life easy kar raha hai!"

**Ayesha ka Outcome:**
- Manual research ki zarurat nahi padti
- Accurate, evidence-based answers milte hain
- Multiple frameworks simultaneously handle ho sakte hain
- Document analysis se compliance gaps identify ho jate hain
- Time aur cost dono save hote hain

---

### Scene 4: UI Testing Module - Farhan Ka Experience

**Farhan ka First Day:**

Farhan ne UI Testing module open kiya. Company ki main website ka URL enter kiya aur scan mode "All (Accessibility + Security)" select kiya.

**Scan Start:**
- Headless Chrome browser ne page load kiya
- DOM analyze hua
- WCAG violations detect huye
- Security headers check huye

**Results:**
- **Accessibility Score:** 68% (Needs Attention - Grade C)
- **Security Score:** 75% (Good - Grade B)
- **Total Violations:** 23
  - Critical: 5 violations
  - Moderate: 8 violations
  - Minor: 10 violations

**Farhan:** "Hmm, accessibility score to improve karna hoga. Dekhte hain ke kya violations hain."

**Violations List:**
1. **Missing Alt Text** (Critical) - 12 images mein alt text missing
2. **Poor Color Contrast** (Moderate) - Text aur background colors ka contrast ratio low hai
3. **Missing Form Labels** (Critical) - 3 forms mein labels missing
4. **Security Headers Missing** (Moderate) - Content-Security-Policy header missing

**Farhan:** "Ab main ML model ki predictions dekh leta hoon."

**ML Model Predictions:**
- Har violation ko automatically severity classify kiya gaya
- Critical violations ko priority di gayi
- Model accuracy: 81.52%

**Farhan:** "Perfect! Ab AI recommendations dekh leta hoon."

**AI Recommendations:**
- Priority-based recommendations mili
- Har recommendation actionable thi
- Specific fixes suggest kiye gaye

**Farhan:** "Ab main authenticated pages ko test karta hoon."

Farhan ne authentication enable kiya:
- Login URL provide kiya
- Username/password diye
- Authenticated page URLs provide kiye

**System Flow:**
1. Login page ki accessibility test hui (BEFORE login)
2. Credentials se login hua
3. Authenticated pages discover kiye gaye
4. Authenticated pages ki testing hui
5. Results combine hoke final report mein dikhaye gaye

**Farhan:** "Ye to bahut smart hai! Authenticated pages bhi automatically test ho gaye."

**Farhan ka Outcome:**
- Automated testing se time save hua
- WCAG violations automatically detect huye
- Security headers check ho gaye
- ML model se severity classification hui
- AI recommendations se fixes easily implement kiye ja sakte hain
- Authenticated pages bhi properly test ho gaye

---

### Scene 5: Azure Checker Module - Ahmed Ka Experience

**Ahmed ka First Day:**

Ahmed ne Azure Checker module open kiya. Usne apni company ki Azure architecture document (PDF) upload kiya.

**Document Upload:**
- File validate hui (size, type, relevance check)
- Text extract hua
- Chunks mein divide hua

**Framework Selection:**
Ahmed ne select kiye:
- Azure Best Practices
- GDPR
- ISO 27001
- ISO 27017 (Cloud Security)

**Analysis Start:**
- Document embeddings create hui
- FAISS similarity search hui
- Top compliance chunks retrieve huye
- Category-wise analysis hui:
  - Security: 78%
  - Identity: 92%
  - Storage: 65%
  - Networking: 80%
  - Monitoring: 70%
  - Compliance: 75%

**Overall Score:** 76% (Partial Compliance)

**Ahmed:** "Hmm, Storage category mein improvement chahiye. Dekhte hain ke kya gaps hain."

**Key Findings:**
- ✅ **Compliant:** Identity management (Azure AD properly configured)
- ⚠️ **Partial:** Storage encryption (customer-managed keys missing)
- ❌ **Non-Compliant:** Monitoring (some logs not properly configured)

**AI Recommendations:**
- Storage encryption ke liye customer-managed keys enable karo
- Monitoring ke liye Azure Monitor properly configure karo
- Specific Azure services ke names suggest kiye gaye

**Checklist Generation:**
- Complete compliance checklist generate hui
- Har requirement ke saath status indicator (✅/⚠️/❌)
- Actionable recommendations mili

**PDF Report:**
- Professional PDF report generate hui
- Executive summary
- Category-wise breakdown
- Visual charts
- Detailed recommendations

**Ahmed:** "Perfect! Ab mujhe clearly pata hai ke kya fix karna hai. Report ko main Sara ko bhej deta hoon."

**Ahmed ka Outcome:**
- Azure configurations automatically analyze ho gaye
- Compliance gaps identify ho gaye
- Detailed checklist mili
- Professional report generate hui
- Time aur effort dono save huye

---

### Scene 6: Schedule Scan Module - Farhan Ka Experience

**Farhan ka Second Week:**

Farhan ko regularly website ko test karna hai. Manual testing har baar time-consuming hai.

**Farhan:** "Main schedule scan use karta hoon taake automatically scans ho jayen."

Farhan ne schedule scan create kiya:
- **Date:** Agle hafte (Friday, 2 PM)
- **URL:** Company website ka URL
- **Email:** Apna email address

**Schedule Created:**
- Schedule database mein store hui
- APScheduler ne job schedule kiya
- Confirmation message mila

**Scheduled Day (Friday, 2 PM):**
- System automatically scan execute kiya
- Whole-site scan run hui
- Results collect huye
- AI recommendations generate huye

**Email Notification:**
- Farhan ko email mili:
  - Scan summary
  - Accessibility score: 72% (improved from 68%)
  - Security score: 78% (improved from 75%)
  - Key findings
  - Recommendations
  - Link to detailed report

**Farhan:** "Perfect! Automatically scan ho gayi aur mujhe email bhi mil gayi. Ab main regularly schedule kar sakta hoon."

**Farhan ka Outcome:**
- Automated scheduled scans
- Email notifications
- Regular monitoring
- Time save hua
- Compliance status track ho raha hai

---

### Scene 7: Activity Logs - Sara Ka Experience

**Sara (CTO) ka Experience:**

Sara ko team activities ko monitor karna hai. Usne Management Dashboard open kiya.

**Management Dashboard:**
- **Today's Activities:**
  - Scans: 5
  - Analyses: 3
  - Reports: 2
  - Uploads: 1

- **This Week's Activities:**
  - Scans: 25
  - Analyses: 15
  - Reports: 10
  - Uploads: 8

**Activity Logs:**
Sara ne filters apply kiye:
- Date range: Last 7 days
- Activity type: All
- Team member: All

**Logs Display:**
- Compliance Team activities (Ayesha ke)
  - Azure analyses
  - Document uploads
  - Compliance reports

- IT Team activities (Farhan aur Ahmed ke)
  - UI testing scans
  - Schedule scans
  - Security scans

**Sara:** "Perfect! Ab mujhe clearly pata hai ke team kya kar rahi hai. Compliance status bhi track ho raha hai."

**Sara ka Outcome:**
- Complete visibility into team activities
- Compliance status monitoring
- Activity trends analysis
- Team productivity measurement
- Audit trail for compliance

---

### Scene 8: Final Outcome - Company Success

**3 Months Baad:**

**TechCorp** ne successfully:
- ✅ **SOC 2 Type II certification** achieve kiya
- ✅ **GDPR compliance** maintain kiya
- ✅ **ISO 27001** requirements implement kiye
- ✅ **Website accessibility** improve kiya (68% → 85%)
- ✅ **Security score** improve kiya (75% → 90%)
- ✅ **Azure compliance** achieve kiya (76% → 88%)

**Team Feedback:**

**Ayesha:** "Complytics platform ne meri life easy kar di. Ab main quickly compliance questions ka jawab de sakti hoon aur documents ko verify kar sakti hoon. Time aur cost dono save huye!"

**Farhan:** "UI Testing module se automated testing ho rahi hai. WCAG violations automatically detect ho rahe hain aur ML model se severity classification ho rahi hai. Bahut helpful hai!"

**Ahmed:** "Azure Checker module se configurations automatically analyze ho rahe hain. Compliance gaps identify ho rahe hain aur detailed reports mil rahe hain. Perfect!"

**Sara:** "Management Dashboard se team activities ko monitor kar sakti hoon. Compliance status track ho raha hai aur reports easily generate ho rahe hain. Excellent platform!"

**CEO:** "Complytics platform ne hamari compliance journey ko completely transform kar diya. Ab hum confidently multiple frameworks ko handle kar sakte hain. Great investment!"

---

### Key Takeaways from Story:

1. **Compliance Chatbot** - Ayesha ko accurate, evidence-based answers milte hain. Multiple frameworks simultaneously handle ho sakte hain. Document analysis se compliance gaps identify hote hain.

2. **UI Testing Module** - Farhan ko automated website testing milti hai. WCAG violations automatically detect hote hain. ML model se severity classification hoti hai. Authenticated pages bhi properly test hote hain.

3. **Azure Checker Module** - Ahmed ko Azure configurations automatically analyze hote hain. Compliance gaps identify hote hain. Detailed checklists aur reports milte hain.

4. **Schedule Scan Module** - Farhan ko automated scheduled scans milti hain. Email notifications milte hain. Regular monitoring possible hai.

5. **Activity Logs** - Sara ko complete visibility milti hai. Team activities track hoti hain. Compliance status monitor hota hai.

**Final Message:**
Complytics platform ek comprehensive solution hai jo companies ko multiple compliance challenges ko efficiently handle karne mein madad karta hai. AI-powered intelligence, automation, aur user-friendly interface ke combination se compliance management easy aur effective ho jata hai.

---

## 1. Project Overview (Mukhtasir Jaaiza)

**Complytics** ek comprehensive compliance management platform hai jo companies ko multiple compliance frameworks ke against apni websites, cloud configurations, aur documents ko test aur verify karne mein madad karta hai.

### Kya Problem Solve Karta Hai?

Aaj kal har company ko multiple compliance standards follow karne padte hain:
- **GDPR** (European customers ke liye)
- **ISO 27001** (Information security ke liye)
- **SOC 2** (Enterprise customers ko satisfy karne ke liye)
- **HIPAA** (Healthcare data ke liye)
- **PCI DSS** (Payment processing ke liye)
- **WCAG** (Website accessibility ke liye)
- Aur bhi bahut se...

Manual compliance checking bahut time-consuming aur error-prone hoti hai. Complytics platform automation aur AI use karke ye sab kaam easily aur accurately karta hai.

---

## 2. Compliance Types Aur Hamara Target

### Compliance Ke Types:

1. **Security Compliance** - Data security, encryption, access controls
   - ISO 27001, SOC 2, NIST
   
2. **Privacy Compliance** - Data protection, user rights
   - GDPR, CCPA, HIPAA
   
3. **Financial Compliance** - Payment security, financial reporting
   - PCI DSS, SOX
   
4. **Accessibility Compliance** - Website accessibility for disabled users
   - WCAG 2.1, Section 508
   
5. **Cloud Compliance** - Cloud infrastructure security
   - ISO 27017, ISO 27018, Azure Best Practices

### Hamara Target:

Hum **multiple compliance frameworks** ko simultaneously handle karte hain:
- ✅ **GDPR** - Privacy regulations
- ✅ **ISO 27001** - Information security management
- ✅ **SOC 2** - Security controls for service organizations
- ✅ **HIPAA** - Healthcare data protection
- ✅ **PCI DSS** - Payment card industry security
- ✅ **NIST** - Cybersecurity framework
- ✅ **CCPA** - California privacy law
- ✅ **ISO 13485** - Medical devices quality
- ✅ **DRAP** - Pakistan drug regulatory authority
- ✅ **WCAG 2.1** - Web accessibility guidelines
- ✅ **Azure Best Practices** - Cloud security standards

---

## 3. System Kya Offer Karta Hai?

### Main Modules:

1. **Compliance Chatbot** - AI-powered chatbot jo compliance questions ka intelligent jawab deta hai
2. **UI Testing Module** - Website accessibility aur security testing
3. **Azure Checker Module** - Azure cloud configurations ko compliance frameworks ke against check karta hai
4. **Schedule Scan Module** - Automated scheduled scans with email notifications
5. **Activity Logs** - Complete audit trail of all activities

### Key Features:

- ✅ **AI-Powered Analysis** - Gemini AI use karke intelligent recommendations
- ✅ **Automated Testing** - Headless browser automation se website scanning
- ✅ **Document Analysis** - Uploaded documents ko compliance frameworks ke against check
- ✅ **RAG System** - Retrieval-Augmented Generation se accurate, evidence-based answers
- ✅ **ML Model Integration** - Accessibility violations ko automatically severity classify karta hai
- ✅ **Role-Based Access** - Different teams ko different permissions
- ✅ **Comprehensive Reporting** - Detailed PDF reports with recommendations

---

## 4. Role-Based Access Control (RBAC) - Kyon Aur Kaise?

### Kyon RBAC Use Karte Hain?

**Security aur Accountability ke liye:**
- Har team ko sirf wahi features access karne chahiye jo unke kaam se related hain
- Superadmin ko sab kuch control karna chahiye
- Compliance team ko compliance modules access karne chahiye
- IT team ko technical modules access karne chahiye
- Management team ko reports aur analytics dekhne chahiye

### Roles Aur Unke Permissions:

1. **Superadmin**
   - ✅ Sab kuch access (full system control)
   - ✅ User management
   - ✅ All modules access
   - ✅ System configuration

2. **Admin**
   - ✅ Organization-level control
   - ✅ Team member management
   - ✅ All compliance modules
   - ✅ Reports aur analytics

3. **Compliance Team**
   - ✅ Compliance Chatbot
   - ✅ Azure Checker Module
   - ✅ Document uploads
   - ✅ Compliance reports
   - ✅ Own activity logs
   - ❌ UI Testing (IT team ka kaam)
   - ❌ User management

4. **IT Team**
   - ✅ UI Testing Module
   - ✅ Schedule Scans
   - ✅ Security scans
   - ✅ Accessibility testing
   - ✅ Own activity logs
   - ❌ Compliance Chatbot
   - ❌ Azure Checker

5. **Management Team**
   - ✅ All reports aur analytics
   - ✅ Team activity logs (sab teams ke)
   - ✅ Dashboard views
   - ✅ Summary reports
   - ❌ Direct module access (sirf monitoring)

### Implementation:

- **JWT Tokens** - Authentication ke liye
- **Role Checking** - Har API endpoint par role verify hota hai
- **Protected Routes** - Frontend mein role-based route protection
- **Database Level** - MongoDB mein role-based queries

---

## 5. IEEE Document Upload - Security Compliance Framework?

**Sawal:** Agar main IEEE document upload karun, to kya wo security compliance framework ke taur par consider hoga?

**Jawab:** **Nahi, IEEE documents automatically reject ho jayenge.**

### Kyon?

IEEE (Institute of Electrical and Electronics Engineers) documents usually **technical standards** hote hain, **compliance frameworks** nahi. Hamara system intelligently detect karta hai ke document compliance framework hai ya nahi.

### Document Classification Logic:

System document ko analyze karke check karta hai:
- ✅ **Accept Karta Hai:**
  - Privacy policies
  - Terms and conditions
  - Security policies
  - Compliance documents
  - Azure configuration documents

- ❌ **Reject Karta Hai:**
  - ISO/IEC standards (ISO 27001 documents themselves)
  - SOC 2 framework documents
  - NIST framework documents
  - PCI DSS standard documents
  - **IEEE technical standards**
  - Personal CVs
  - Academic papers
  - Game guides
  - Recipes

### Detection Method:

System **AI-powered classification** use karta hai jo document content ko semantically analyze karta hai. Agar document mein compliance framework indicators milte hain (jaise "ISO/IEC 27001", "SOC 2 controls", "IEEE standards"), to wo automatically reject ho jata hai.

**Reason:** Compliance Chatbot already in frameworks ke documents se trained hai. User ko framework documents upload karne ki zarurat nahi - chatbot already in frameworks ko janta hai.

---

## 6. RAG Capabilities (Retrieval-Augmented Generation)

### RAG Kya Hai?

**RAG** ek AI technique hai jo **document retrieval** aur **AI generation** ko combine karta hai.

### Kaise Kaam Karta Hai?

1. **Document Storage:**
   - Compliance framework documents (GDPR, ISO 27001, etc.) ko PDF format mein store kiya jata hai
   - Documents ko small chunks mein divide kiya jata hai (1000 characters per chunk)

2. **Embedding Creation:**
   - Har chunk ka **embedding** (semantic vector) create hota hai
   - **SentenceTransformer** model use hota hai (`all-MiniLM-L6-v2`)
   - Embeddings **FAISS index** mein store hote hain (fast similarity search ke liye)

3. **Query Processing:**
   - User query ka embedding create hota hai
   - FAISS index mein **similarity search** hoti hai
   - Top 3 most relevant chunks retrieve hote hain

4. **Response Generation:**
   - Retrieved chunks ko **Gemini AI** ko context ke taur par diye jate hain
   - AI context ko use karke accurate, evidence-based answer generate karta hai
   - Har answer mein **exact citations** hote hain (control IDs, article numbers)

### Benefits:

- ✅ **Accurate Answers** - Documents se direct evidence
- ✅ **Up-to-Date** - Documents update karne se answers automatically update
- ✅ **Evidence-Based** - Har answer ke saath exact citations
- ✅ **No Hallucination** - AI sirf provided documents se answer deta hai

---

## 7. RAG Chatbot - Common Questions & Answers

### Q1: Chatbot sirf keyword matching karta hai ya semantic understanding?

**A:** **Pure semantic understanding** - keyword matching bilkul nahi. Agar aap puchte hain "data protection rules for european customers", chatbot intelligently detect karta hai ke ye GDPR related query hai, even if "GDPR" word explicitly mention nahi hua.

### Q2: Chatbot multiple frameworks ko simultaneously handle kar sakta hai?

**A:** **Haan!** Agar aap puchte hain "What are encryption requirements for GDPR and PCI DSS?", chatbot dono frameworks ke experts ko simultaneously consult karta hai aur separate sections mein answers deta hai.

### Q3: Chatbot context maintain karta hai?

**A:** **Haan!** Agar aap pehle puchte hain "What is ISO 27001?" aur phir follow-up mein "What are the monitoring controls for this framework?", chatbot intelligently detect karta hai ke "this framework" se ISO 27001 ka reference hai.

### Q4: Chatbot document analysis kar sakta hai?

**A:** **Haan!** Aap apni privacy policy ya security policy upload kar sakte hain. Chatbot document ko analyze karke compliance gaps identify karta hai aur specific control IDs ke saath recommendations deta hai.

### Q5: Chatbot non-compliance queries ko handle karta hai?

**A:** **Haan!** Agar aap cooking recipes ya movies ke baare mein puchte hain, chatbot politely decline karta hai kyunke ye compliance-related nahi hai. System **guardrails** use karta hai jo semantically check karta hai ke query relevant hai ya nahi.

### Q6: Chatbot cache karta hai?

**A:** **Haan!** Common questions (jaise "What is GDPR?") cache hote hain for fast responses. Lekin document-specific queries cache nahi hote kyunke har document different hota hai.

### Q7: Chatbot step-by-step implementation guidance deta hai?

**A:** **Haan!** Agar aap puchte hain "How should we achieve SOC 2 certification?", chatbot structured 8-step implementation plan deta hai with specific controls aur AWS/Azure recommendations.

---

## 8. UI Testing Module - Complete Flow

### Module Kya Karta Hai?

UI Testing Module websites ko **accessibility (WCAG)** aur **security** ke liye test karta hai. Ye automated scanning use karke violations detect karta hai aur AI-powered recommendations provide karta hai.

### Kaise Kaam Karta Hai?

#### Step 1: URL Input
- User website ka URL enter karta hai
- Scan mode select karta hai:
  - **All** - Accessibility + Security
  - **Accessibility** - Sirf WCAG testing
  - **Security** - Sirf security testing

#### Step 2: Page Loading
- **Headless Chrome browser** use hota hai (GUI ke bina)
- Page load hota hai aur DOM (Document Object Model) analyze hota hai
- JavaScript-rendered content bhi properly load hota hai

#### Step 3: Accessibility Testing (WCAG)
- **axe-core library** use hoti hai (industry standard accessibility testing tool)
- Page ko WCAG 2.1 guidelines ke against check kiya jata hai
- Violations detect hote hain:
  - Missing alt text for images
  - Poor color contrast
  - Missing form labels
  - Keyboard navigation issues
  - ARIA attributes missing/incorrect

#### Step 4: Security Testing
- **SSL Certificate** check hota hai (valid, expired, self-signed?)
- **Security Headers** verify hote hain:
  - `Content-Security-Policy` - XSS attacks se protection
  - `X-Frame-Options` - Clickjacking se protection
  - `Strict-Transport-Security` - HTTPS enforcement
  - `X-Content-Type-Options` - MIME type sniffing prevention
  - `Referrer-Policy` - Referrer information control
- **Vulnerabilities** detect hote hain (common web vulnerabilities)

#### Step 5: Results Processing
- Violations ko collect kiya jata hai
- **ML Model** har violation ko severity classify karta hai (Critical/Moderate/Minor)
- Scores calculate hote hain:
  - **Accessibility Score** - WCAG compliance percentage
  - **Security Score** - Security headers aur SSL compliance percentage
  - **Overall Grade** - Combined grade (A/B/C/D/F)

#### Step 6: AI Recommendations
- **Gemini AI** scan results ko analyze karta hai
- Priority-based recommendations generate hote hain
- Har recommendation actionable hota hai (kaise fix karna hai)

#### Step 7: Report Generation
- Detailed report generate hota hai
- Violations list with severity
- Security headers status
- Recommendations
- Export options (PDF, Excel)

### Security Headers Examples:

1. **Content-Security-Policy (CSP)**
   - **Kya Hai:** XSS attacks se protection
   - **Example:** `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'`
   - **Kyon Important:** Malicious scripts ko execute hone se rokti hai

2. **X-Frame-Options**
   - **Kya Hai:** Clickjacking se protection
   - **Example:** `X-Frame-Options: DENY` ya `X-Frame-Options: SAMEORIGIN`
   - **Kyon Important:** Website ko iframe mein embed hone se rokti hai

3. **Strict-Transport-Security (HSTS)**
   - **Kya Hai:** HTTPS enforcement
   - **Example:** `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - **Kyon Important:** HTTP se HTTPS redirect ko force karta hai

4. **X-Content-Type-Options**
   - **Kya Hai:** MIME type sniffing prevention
   - **Example:** `X-Content-Type-Options: nosniff`
   - **Kyon Important:** Browser ko content type ko sniff karne se rokti hai

### Accessibility Issues Examples:

1. **Missing Alt Text**
   - **Issue:** Images mein alt attribute missing
   - **Impact:** Screen readers images ko describe nahi kar sakte
   - **Fix:** Har image mein descriptive alt text add karo

2. **Poor Color Contrast**
   - **Issue:** Text aur background colors ka contrast ratio low hai
   - **Impact:** Visually impaired users text padh nahi sakte
   - **Fix:** WCAG AA standard ke mutabiq contrast ratio maintain karo (minimum 4.5:1)

3. **Missing Form Labels**
   - **Issue:** Form inputs ke saath `<label>` tags missing
   - **Impact:** Screen readers form fields ko identify nahi kar sakte
   - **Fix:** Har input ke saath associated label add karo

4. **Keyboard Navigation Issues**
   - **Issue:** Website keyboard se navigate nahi ho sakti
   - **Impact:** Keyboard-only users website use nahi kar sakte
   - **Fix:** Tab order aur focus indicators add karo

### Authenticated Pages Handling:

#### Problem:
Kuch pages login ke baad hi accessible hote hain. Unhein test kaise karein?

#### Solution:

**Whole-Site Scan Mode:**
1. **Login Page Detection:**
   - System automatically login pages detect karta hai (URL patterns se)
   - DOM analysis se login forms identify hote hain

2. **Login Page Accessibility Test:**
   - **Pehle** login page ki accessibility test hoti hai (BEFORE login, public state mein)
   - Results store hote hain

3. **Authentication:**
   - Provided credentials se login hota hai
   - **Selenium** use karke login form fill hota hai:
     - Username field detect hota hai
     - Password field detect hota hai
     - Submit button click hota hai
   - Session cookies extract hote hain

4. **Authenticated Pages Discovery:**
   - Login ke baad website ko **re-crawl** kiya jata hai
   - Authenticated pages discover hote hain
   - Links follow kiye jate hain (authenticated state mein)

5. **Authenticated Pages Testing:**
   - Discovered authenticated pages ki accessibility testing hoti hai
   - Session cookies use karke authenticated requests bheje jate hain

6. **Results Aggregation:**
   - Login page aur authenticated pages dono ke results combine hote hain
   - Final report mein dono sets of results include hote hain

**Specific URLs Scan Mode:**
1. User **login URL** provide karta hai
2. User **authenticated page URLs** provide kar sakta hai (optional)
3. Pehle login page test hoti hai
4. Phir authentication hoti hai
5. Phir authenticated pages test hote hain (provided URLs ya discovered URLs)
6. Phir specific URLs test hote hain (excluding login page)

### Login Form Detection:

System intelligently login forms ko detect karta hai:

1. **DOM Analysis:**
   - `<form>` elements ko search karta hai
   - Form fields ko identify karta hai:
     - Username/email fields (type="text", type="email", name="username", name="email")
     - Password fields (type="password")
     - Submit buttons (type="submit", button text "login", "sign in")

2. **Pattern Matching:**
   - Common login form patterns:
     - Username field + Password field + Submit button
     - Email field + Password field + Submit button
     - Multiple variations handle hote hain

3. **Fallback Methods:**
   - Agar standard form nahi milta, to:
     - Input fields ko search karta hai
     - Password field ko identify karta hai
     - Nearest submit button ko find karta hai

### Scoring System:

#### Accessibility Score:

**Formula:**
```
Accessibility Score = 100 - (Violations × Deduction per Violation)
```

**Severity-Based Deductions:**
- **Critical Violations:** 5 points deduction per violation
- **Moderate Violations:** 2 points deduction per violation
- **Minor Violations:** 1 point deduction per violation

**Grade Assignment:**
- **90-100:** Excellent (A)
- **75-89:** Good (B)
- **50-74:** Needs Attention (C)
- **25-49:** Critical (D)
- **0-24:** Very Critical (F)

#### Security Score:

**Components:**
1. **SSL Certificate:** 30 points
   - Valid SSL: 30 points
   - Self-signed: 15 points
   - Expired: 0 points
   - No SSL: 0 points

2. **Security Headers:** 70 points (10 points per header)
   - Content-Security-Policy: 10 points
   - X-Frame-Options: 10 points
   - Strict-Transport-Security: 10 points
   - X-Content-Type-Options: 10 points
   - Referrer-Policy: 10 points
   - Permissions-Policy: 10 points
   - X-XSS-Protection: 10 points

**Grade Assignment:**
- **90-100:** Excellent (A)
- **75-89:** Good (B)
- **50-74:** Needs Attention (C)
- **25-49:** Critical (D)
- **0-24:** Very Critical (F)

### ML Model Integration:

#### Model Details:

**Model Type:** Random Forest Classifier (300 trees)

**Training Data:**
- **Dataset:** `ml/data/web content accessibility.csv`
- **Rows:** 5,472 accessibility violations
- **Features:**
  - `rule_id` - WCAG rule identifier
  - `impact` - Impact level (Critical, Serious, Moderate, Minor)
  - `nodes` - Number of affected DOM nodes
  - `has_help_url` - Help documentation available?
  - `target_text_len` - Length of target element text
  - `has_aria` - ARIA attributes present?
  - `is_interactive` - Interactive element?

**Target:** `severity` (Critical/Moderate/Minor)

**Accuracy:** **81.52%** overall accuracy

**Class Performance:**
- **Critical (High):** Precision 85.7%, Recall 75.1%
- **Moderate:** Precision 77.5%, Recall 79.9%
- **Minor (Low):** Precision 91.1%, Recall 89.5%

#### Integration Flow:

1. **Violation Detection:**
   - WCAG scan violations detect karta hai
   - Har violation ka metadata extract hota hai

2. **Feature Extraction:**
   - Violation se features extract hote hain:
     - Rule ID
     - Impact level
     - Number of nodes
     - Help URL availability
     - Target text length
     - ARIA attributes presence
     - Interactive element flag

3. **ML Prediction:**
   - Trained model (`ml/outputs/model.joblib`) load hota hai
   - Features ko model mein feed kiya jata hai
   - Model severity predict karta hai (Critical/Moderate/Minor)

4. **Results Integration:**
   - Predicted severity violation ke saath attach hoti hai
   - UI mein severity badges dikhaye jate hain
   - Scoring mein severity-based deductions apply hote hain
   - AI recommendations mein severity consider hoti hai

#### Benefits:

- ✅ **Automatic Classification** - Manual triage ki zarurat nahi
- ✅ **Consistent Severity** - Same violations ko same severity milti hai
- ✅ **Priority-Based Fixing** - Critical violations pehle fix kiye ja sakte hain
- ✅ **Fast Processing** - <5ms per violation prediction

---

## 9. Azure Checker Module - Complete Flow

### Module Kya Karta Hai?

Azure Checker Module Azure cloud configuration documents ko upload karne ki facility deta hai aur unhein multiple compliance frameworks (Azure Best Practices, GDPR, ISO 27001, ISO 27017, ISO 27018) ke against analyze karta hai.

### Supported Document Types:

1. **PDF Files** (`.pdf`)
   - Azure architecture documents
   - Security policies
   - Configuration guides

2. **Word Documents** (`.docx`, `.doc`)
   - Security runbooks
   - Policy documents
   - Architecture decks

3. **Text Files** (`.txt`)
   - Configuration exports
   - Policy text files

4. **JSON Files** (`.json`)
   - Azure Policy exports
   - ARM template configurations
   - Infrastructure as Code files

### Document Analysis Flow:

#### Step 1: Document Upload
- User document upload karta hai
- System file ko validate karta hai:
  - File size check (max 50MB)
  - File type check
  - **Relevance check** - Azure/cloud related hai ya nahi?
  - Image files automatically reject hote hain

#### Step 2: Text Extraction
- Document se text extract hota hai:
  - PDF: PyPDF2/pdfplumber use hota hai
  - DOCX: python-docx use hota hai
  - TXT: Direct read
  - JSON: Parse karke text extract
- Text ko clean kiya jata hai (whitespace, special characters)
- Text ko chunks mein divide kiya jata hai (1000 characters per chunk)

#### Step 3: Framework Selection
- User framework select karta hai:
  - Azure Best Practices
  - GDPR
  - ISO 27001
  - ISO 27017 (Cloud Security)
  - ISO 27018 (Cloud Privacy)
- Multiple frameworks simultaneously select kiye ja sakte hain

#### Step 4: Embedding Creation
- Har framework ka apna **embedding engine** hota hai
- Document chunks ka embedding create hota hai
- **SentenceTransformer** model use hota hai (`all-MiniLM-L6-v2`)

#### Step 5: Similarity Search
- **FAISS index** use hota hai (fast vector similarity search)
- Document embeddings ko framework-specific FAISS index mein search kiya jata hai
- Top 3 most similar compliance chunks retrieve hote hain
- **Cosine similarity** use hoti hai (0-1 range)

#### Step 6: Compliance Analysis
- Document content ko compliance requirements se compare kiya jata hai
- **Category-wise analysis** hoti hai:
  - **Security** - Encryption, SSL/TLS, Firewall, Authentication
  - **Identity** - Azure AD, Active Directory, SSO
  - **Storage** - Storage accounts, Blob, Encryption
  - **Networking** - Virtual Network, VPN, Load Balancer
  - **Monitoring** - Logging, Alerts, Metrics
  - **Compliance** - Regulatory compliance requirements
  - **Governance** - Policy management, resource organization

#### Step 7: AI Validation
- **Gemini AI** har category ko analyze karta hai
- AI se milta hai:
  - **Status** - Compliant/Partial/Non-Compliant
  - **Gaps** - Missing requirements
  - **Recommendations** - How to fix

#### Step 8: Score Calculation

**Category Score:**
- FAISS similarity se average similarity calculate hoti hai
- Similarity ko 0-100 percent mein convert kiya jata hai
- Example: 0.82 similarity → 82% score

**Framework Score:**
- Har selected framework ke liye independently score calculate hota hai
- Category scores ka average framework score hota hai

**Overall Score:**
- Sab frameworks ke scores ka average overall score hota hai
- **Grade Assignment:**
  - **>=80:** Compliant
  - **60-79:** Partial Compliance
  - **<60:** Non-Compliant

#### Step 9: Checklist Generation

**Checklist Items:**
- Har compliance requirement ke liye checklist item create hota hai
- Items ko categories mein organize kiya jata hai
- Har item mein:
  - Requirement description
  - Compliance status (Compliant/Partial/Non-Compliant)
  - Evidence from document (if found)
  - Recommendations (if non-compliant)

**Checklist Format:**
- Structured checklist format
- Category-wise grouping
- Status indicators (✅ Compliant, ⚠️ Partial, ❌ Non-Compliant)
- Actionable recommendations

#### Step 10: Report Generation

**PDF Report Includes:**
1. **Executive Summary**
   - Overall compliance score
   - Framework-wise scores
   - Key findings

2. **Compliance Scores**
   - Category-wise breakdown
   - Framework-wise comparison
   - Visual charts (bar charts, gauges)

3. **Key Findings**
   - Compliant areas
   - Non-compliant areas
   - Partial compliance areas

4. **Detailed Analysis**
   - Category-wise detailed findings
   - Evidence from document
   - Gap analysis

5. **Recommendations**
   - Priority-based recommendations
   - Implementation guidance
   - Best practices

6. **Compliance Checklist**
   - Complete checklist
   - Status indicators
   - Action items

### Fetched Settings Analysis:

**Azure Settings Detection:**
- Document mein Azure-specific settings detect hote hain:
  - Azure AD configurations
  - Key Vault settings
  - Storage encryption settings
  - Network security groups
  - Monitoring configurations

**Compliance Mapping:**
- Detected settings ko compliance requirements se map kiya jata hai
- Missing settings identify hote hain
- Non-compliant settings flag hote hain

---

## 10. Schedule Scan Module - Complete Flow

### Module Kya Karta Hai?

Schedule Scan Module UI testing scans ko **future dates par schedule** karne ki facility deta hai. System automatically scheduled time par scan execute karta hai aur email notifications bhejta hai.

### Kaise Kaam Karta Hai?

#### Step 1: Schedule Creation
- User schedule scan page par jata hai
- **Date aur time select** karta hai (future date honi chahiye)
- **URL provide** kar sakta hai ya **previous URL** use kar sakta hai
- Schedule create karta hai

#### Step 2: Schedule Storage
- Schedule **MongoDB database** mein store hota hai (`scheduled_scans` collection)
- Schedule details:
  - Organization ID
  - Scheduled by (user ID)
  - Email address (notifications ke liye)
  - Scheduled for (timestamp)
  - URL (optional)
  - Status (scheduled/running/completed/failed/cancelled)

#### Step 3: Job Scheduling
- **APScheduler** use hota hai (Python task scheduler)
- Job specific date/time par trigger hoti hai
- Job ID schedule ID se match hota hai
- Server restart par jobs automatically rehydrate hote hain

#### Step 4: Job Execution
- Scheduled time par job automatically execute hoti hai
- Status "scheduled" se "running" mein change hota hai
- **URL Resolution:**
  1. Priority 1: Schedule mein stored URL
  2. Priority 2: Last whole-site scan URL
  3. Priority 3: Last single-page scan URL
  4. Error: Agar koi URL nahi milti, scan fail ho jati hai

#### Step 5: Scan Execution
- **Whole-site scan** execute hoti hai
- Scan parameters:
  - max_pages: 50
  - max_depth: 3
  - scan_mode: "all" (Accessibility + Security)
  - parallel_scans: 3

#### Step 6: Result Processing
- Scan results collect hote hain
- **AI recommendations** generate hote hain
- Results database mein store hote hain (`ui_testing_site_results`)

#### Step 7: Email Notification
- Scan complete hone par **email send** hoti hai
- Email mein include hota hai:
  - Scan summary
  - Accessibility score
  - Security score
  - Total pages scanned
  - Key findings
  - Recommendations
  - Link to detailed report

#### Step 8: Status Update
- Status "running" se "completed" mein change hota hai
- Agar error aaye, status "failed" ho jata hai
- Error message store hota hai

### Schedule Management:

**List Schedules:**
- User apne sab schedules dekh sakta hai
- Filter by status (scheduled/running/completed/failed)
- Sort by scheduled date

**Cancel Schedule:**
- User pending schedules ko cancel kar sakta hai
- Cancelled schedules execute nahi hote
- Status "cancelled" ho jata hai

**Permissions:**
- Sirf **compliance_team**, **admin**, aur **superadmin** roles schedule kar sakte hain
- Other roles ko 403 error milta hai

---

## 11. Activity Logs - All Dashboards

### Activity Logs Kya Hain?

Activity Logs ek **complete audit trail** hain jo system mein hone wali har activity ko track karta hai. Har dashboard mein different types ke logs hote hain.

### Compliance Team Dashboard Logs:

**Tracked Activities:**
1. **Azure Compliance Analyses**
   - Document uploads
   - Analysis executions
   - Report generations
   - Checklist creations

2. **Document Uploads**
   - File uploads
   - Document processing
   - Text extraction

3. **Compliance Reports**
   - Report generations
   - Report downloads
   - Report sharing

4. **Compliance Checklists**
   - Checklist generations
   - Checklist updates
   - Checklist completions

**Log Details:**
- Activity type
- Activity label
- Description
- Timestamp
- Status (success/failed)
- User email
- User role

**Filters:**
- Date range (start date, end date)
- Activity type
- Status (success/failed)

### IT Team Dashboard Logs:

**Tracked Activities:**
1. **UI Testing Scans**
   - Single page scans
   - Whole-site scans
   - Specific URLs scans
   - Scan results

2. **Schedule Scans**
   - Schedule creations
   - Schedule executions
   - Schedule cancellations
   - Scan completions

3. **Security Scans**
   - SSL certificate checks
   - Security headers checks
   - Vulnerability scans

4. **Accessibility Scans**
   - WCAG violations
   - Accessibility scores
   - Violation fixes

**Log Details:**
- Activity type
- Activity label
- Description
- URL scanned
- Scan mode
- Accessibility score
- Security score
- Timestamp
- Status
- User email
- User role

**Filters:**
- Date range
- Activity type
- Status
- Scan mode

### Management Team Dashboard Logs:

**Tracked Activities (All Teams):**
1. **Compliance Team Activities**
   - Azure analyses
   - Document uploads
   - Reports
   - Checklists

2. **IT Team Activities**
   - UI testing scans
   - Schedule scans
   - Security scans

3. **Cross-Team Summary**
   - Today's activities
   - This week's activities
   - Activity trends

**Log Details:**
- Activity type
- Activity label
- Description
- Team member (email)
- Team member role
- Timestamp
- Status

**Filters:**
- Date range
- Activity type
- Team member
- Status

**Summary Statistics:**
- Today's scans
- Today's analyses
- Today's reports
- Today's uploads
- Today's checklists
- This week's totals

### Activity Log Storage:

**Database Collection:** `activity_logs`

**Log Entry Structure:**
```json
{
  "_id": "log_id",
  "organization_id": "org_id",
  "user_id": "user_id",
  "user_email": "user@example.com",
  "user_role": "compliance_team",
  "activity_type": "azure_analysis",
  "activity_label": "Azure Compliance Analysis",
  "description": "Analyzed Azure configuration document",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "success",
  "details": {
    "framework": "ISO 27001",
    "score": 85,
    "document_name": "azure_config.pdf"
  }
}
```

### Benefits:

- ✅ **Complete Audit Trail** - Har activity track hoti hai
- ✅ **Accountability** - Har action ke saath user information
- ✅ **Compliance** - Regulatory compliance ke liye audit logs
- ✅ **Debugging** - Issues ko trace karne mein madad
- ✅ **Analytics** - Activity trends analyze karne ke liye

---

## 12. Summary - Key Takeaways

### Platform Strengths:

1. **Comprehensive Coverage**
   - Multiple compliance frameworks
   - Multiple testing modules
   - Complete audit trail

2. **AI-Powered Intelligence**
   - RAG system for accurate answers
   - ML model for severity classification
   - AI recommendations for fixes

3. **Automation**
   - Automated website scanning
   - Scheduled scans
   - Automated report generation

4. **User-Friendly**
   - Layman-friendly interface
   - Clear reports
   - Actionable recommendations

5. **Security**
   - Role-based access control
   - Secure authentication
   - Audit logs

### Use Cases:

1. **Compliance Officers** - Compliance frameworks ko understand karna aur documents ko verify karna
2. **IT Teams** - Website accessibility aur security ko test karna
3. **Cloud Engineers** - Azure configurations ko compliance ke against verify karna
4. **Management** - Team activities ko monitor karna aur reports dekhna

### Future Enhancements:

- More compliance frameworks support
- AWS aur GCP checker modules
- Advanced ML models
- Real-time monitoring
- Integration with CI/CD pipelines

---

## End of Presentation

**Thank You!**

Koi sawaal ho to zaroor puchhain.

