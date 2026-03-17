# Project Structure - FSI Vessel Arrival Monitor v4

```
Project1/
├── 📋 PRD.md                          # Product Requirements Document (v4.0)
├── 🐍 fsi_monitor.py                  # Main Python application
├── 📘 README.md                        # Project documentation & setup guide
├── 📄 LICENSE                          # MIT License
├── 📊 CODE_VERIFICATION_REPORT.md     # Implementation compliance report
├── 📋 PROJECT_STRUCTURE.md            # This file
│
├── 🚀 DEPLOYMENT FILES
│   ├── Procfile                        # Cloud deployment: web: python fsi_monitor.py
│   ├── requirements.txt                # Dependencies (empty - stdlib only)
│   └── runtime.txt                     # Python 3.11.8 specification
│
├── 🔧 CONFIGURATION
│   └── .gitignore                      # Git ignore rules
│
└── 📦 RUNTIME FILES (Generated on first run)
    └── fsi_vessels_db.json             # Local vessel database (30-day rolling)
```

---

## File Descriptions

### Core Files

#### **PRD.md** (Product Requirements Document)
- **Purpose**: Complete specification of all requirements
- **Version**: 4.0 (Production Ready)
- **Sections**:
  - Executive summary
  - Data sources (Barcelona, Bilbao, Marín, VesselFinder)
  - UI requirements
  - Inspection request generator
  - Daily email feature (⭐ NEW)
  - Database schema
  - API endpoints
  - Technical requirements
  - Cloud deployment
  - User stories & acceptance criteria

#### **fsi_monitor.py** (Main Application)
- **Language**: Python 3.11+
- **Framework**: Python standard library (no external dependencies)
- **Size**: ~392 lines
- **Components**:
  - Database management (load, save, cleanup)
  - Data fetching functions:
    - `fetch_vf_expected()` - VesselFinder scraping
    - `fetch_bcn_arrivals()` - Barcelona CSV
    - `fetch_bilbao()` - Bilbao HTML + IMO lookup
    - `fetch_marin()` - Marín HTML scraping
    - `lookup_imo()` - VesselFinder IMO search
  - HTTP server with API endpoints
  - Embedded HTML/CSS/JavaScript dashboard

#### **README.md**
- Getting started guide
- Feature overview
- Installation instructions
- Local development
- Cloud deployment guides (Render, Railway, Heroku)
- Data sources information
- Troubleshooting

#### **CODE_VERIFICATION_REPORT.md**
- Detailed compliance analysis against PRD
- Lists what's working (✅)
- Lists what's missing (❌)
- Priority fixes needed
- ~70% compliance rate

---

## How to Run

### Local Development
```bash
# Navigate to Project1 directory
cd /Users/illyagitlevych/Desktop/Project1

# Run the app
python fsi_monitor.py

# The app will:
# 1. Start server on http://localhost:8090
# 2. Open browser automatically
# 3. Display dashboard with all ports/flags selected
# 4. Fetch data from 4 sources
```

### Cloud Deployment
```bash
# Option 1: Render.com
# 1. Push to GitHub
# 2. Connect GitHub repo to Render
# 3. Set runtime: Python 3.11.8
# 4. Deploy (Procfile will be detected automatically)

# Option 2: Railway.app
# 1. Push to GitHub
# 2. Create new project, connect GitHub
# 3. Set PORT env variable (Railway auto-sets it)
# 4. Deploy

# Option 3: Heroku (Legacy)
# 1. heroku login
# 2. heroku create
# 3. git push heroku main
# 4. heroku config:set PORT=8090 (if needed)
```

---

## Key Features

### ✅ Fully Working
- Dashboard with live filtering
- Multi-select port and flag filters
- Vessel search by name/IMO
- Sortable table (click headers)
- CSV export
- Database persistence (30-day history)
- Inspection request message generation
- VesselFinder link generation
- Mobile-responsive design
- No external dependencies

### ⚠️ Needs Implementation
1. **Daily email feature** (6:00 AM automated)
2. **Barcelona dual fallback** (JSON API → CSV fallback)
3. **IMO lookup caching** (performance optimization)
4. **Message format fixes** (date format + no per-flag splitting)
5. **Version update to v4.0**

---

## Data Sources

### 1. Barcelona Port Authority (Open Data)
- **URL**: CSV export
- **Coverage**: 7 days ahead
- **Vessels**: 100+
- **Data**: Name, IMO, flag, type, ETA, origin, agent, line, LOA, beam

### 2. Bilbao Port Authority
- **URL**: HTML scraping + IMO lookup
- **Coverage**: 3 weeks ahead
- **Vessels**: ~68
- **Data**: Name, flag, GT, LOA, origin, ETA + IMO lookup

### 3. Marín Port Authority
- **URL**: HTML scraping
- **Coverage**: 10 days ahead
- **Vessels**: ~8
- **Data**: Name, origin, destination, agent, type, ETA

### 4. VesselFinder
- **URL**: Port-specific scraping
- **Coverage**: 10 days ahead
- **Vessels**: ~10 per port
- **Data**: Name, IMO, type, ETA, flag, GT, DWT, LOA, beam

---

## Database Schema

**File**: `fsi_vessels_db.json`

```json
{
  "vessels": {
    "9399105_ESBIO": {
      "imo": "9399105",
      "name": "Star Sky",
      "type": "Container Ship",
      "flagCode": "PA",
      "flagName": "Panama",
      "portId": "ESBIO",
      "portName": "Bilbao",
      "firstSeen": "2026-03-17T12:00:00",
      "lastSeen": "2026-03-17T13:00:00",
      "eta": "2026-03-05",
      "lastETA": "2026-03-05",
      "gt": 20000,
      "dwt": 30000,
      "built": "2015",
      "loa": "200",
      "beam": "32",
      "origin": "Singapore",
      "dest": "Hamburg",
      "agent": "Agent Name",
      "line": "Shipping Line",
      "source": "BIO-PA"
    }
  },
  "meta": {
    "created": "2026-03-17T12:00:00",
    "lastRun": "2026-03-17T13:00:00",
    "runs": 42
  }
}
```

---

## API Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /` | Dashboard HTML | HTML page |
| `GET /api/barcelona` | Fetch Barcelona data | `{vessels: [...], count: N, added: N}` |
| `GET /api/bilbao` | Fetch Bilbao data | `{vessels: [...], count: N, added: N}` |
| `GET /api/marin` | Fetch Marín data | `{vessels: [...], count: N, added: N}` |
| `GET /api/port?vf=CODE&pid=ID&pname=NAME` | Fetch VesselFinder data | `{vessels: [...], count: N, added: N}` |
| `GET /api/history` | Get full database | `{vessels: {...}, meta: {...}}` |
| `GET /api/clearold` | Delete >30 day records | `{removed: N, remaining: N}` |

---

## Performance Targets

| Operation | Target | Status |
|-----------|--------|--------|
| Dashboard load | <2 seconds | ✅ |
| Barcelona fetch | ~3 seconds | ✅ |
| Bilbao fetch | ~8 seconds | ✅ |
| Marín fetch | ~2 seconds | ✅ |
| VesselFinder per port | ~2 seconds | ✅ |
| Total refresh | ~20-25 seconds | ✅ |
| Search/filter | <100ms | ✅ |

---

## Next Steps for Development

1. **Add daily email feature**
   - Schedule task for 6:00 AM
   - Filter Cantabria/Galicia + LR/MT/MH
   - Send via SMTP

2. **Implement Barcelona JSON API fallback**
   - Add primary endpoint
   - Add try/except with fallback logic

3. **Add IMO caching**
   - Create in-memory cache dict
   - Add retry logic

4. **Fix message formatting**
   - Update date format to DD-Mon-YYYY
   - Remove per-flag splitting

5. **Update version to v4.0**
   - Update Python code header
   - Update HTML title

---

## Deployment Checklist

- [x] No external dependencies
- [x] Procfile created and tested
- [x] requirements.txt created
- [x] runtime.txt created
- [x] PORT env var support
- [x] HOST set to 0.0.0.0
- [x] CORS enabled
- [x] Database directory writable
- [ ] Daily email implemented (PENDING)
- [ ] Version updated to v4.0 (PENDING)
- [ ] All fixes from verification report applied (PENDING)

---

## Support & Contact

**Product Owner**: Capt. Gitlevych Illya
**Email**: gitlevych.ilya@gmail.com
**Phone**: +34 603 730 040 (WhatsApp)
**LinkedIn**: https://www.linkedin.com/in/gitlevych/

---

**Project Status**: ⚠️ Production-Ready for Manual Monitoring | ❌ Not Ready for Automated Features
