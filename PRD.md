# 📋 FSI Vessel Arrival Monitor — Product Requirements Document (PRD)

**Version**: 4.0  
**Last Updated**: 2026-03-17  
**Status**: ✅ Production Ready  
**Owner**: Capt. Gitlevych Illya (Flag State Inspector)

---

## 1. Executive Summary

**FSI Vessel Arrival Monitor** is a professional web dashboard for monitoring vessel arrivals at Spanish ports (Cantabrian & Galicia regions + Barcelona) and generating formal inspection request communications.

**Key Use Case**: Monitor 200+ scheduled vessel arrivals and generate formal inspection request emails to flag state administrations.

---

## 2. Data Sources & Requirements

### 2.1 Barcelona Port Authority (Open Data API)
- **Status**: ✅ WORKING (dual fallback)
- **Source Type**: CSV + JSON API
- **Vessel Count**: 100+ vessels
- **Forecast Window**: 7 days
- **Primary URL**: `https://opendataportdebarcelona.cat/api/3/action/datastore_search_sql`
- **Fallback URL**: `https://opendatapre.portdebarcelona.cat/...`
- **Requirement**: Automatic fallback if one endpoint fails

### 2.2 Bilbao Port Authority
- **Status**: ✅ WORKING (with IMO lookup)
- **Source Type**: HTML scraping
- **Vessel Count**: 68 vessels
- **Forecast Window**: 3 weeks
- **URL**: `https://www.bilbaoport.eus/en/vessel-activity/scheduled-calls/`
- **Critical Requirement**: For EACH vessel, lookup IMO using name + flag via VesselFinder
  - Cache results (in-memory)
  - Timeout: 8 seconds per lookup
  - Retry: 2 attempts with 0.5s pause
  - Result must include IMO number

### 2.3 Marín Port Authority
- **Status**: ✅ WORKING
- **Source Type**: HTML scraping
- **Vessel Count**: ~8 vessels
- **Forecast Window**: 10 days
- **URL**: `https://www.apmarin.com/es/paginas/buques_esperados`

### 2.4 VesselFinder (Secondary Source)
- **Status**: ✅ WORKING
- **Source Type**: Web scraping
- **Vessel Count**: 10 per port
- **Ports**: Gijón, Avilés, Santander, Pasajes, Bayonne, San Ciprián, Ferrol, A Coruña, Vilagarcía, Vigo
- **Forecast Window**: 10 days

---

## 3. User Interface Requirements

### 3.1 Dashboard
- Title: "FSI Vessel Arrival Monitor v4"
- Live indicator + Last updated time
- Refresh button + CSV export button
- 5 statistics cards (Matched, Live Today, History, Direct PA, VesselFinder)

### 3.2 Port Selector
- **Default Selection**: Gijón, Avilés, Santander, Bilbao, Pasajes, Bayonne, San Ciprián, Ferrol, A Coruña, Marín, Vilagarcía, Vigo
- **Regions**: Cantabrian, Galicia, Mediterranean
- **Mark Direct Sources**: Barcelona 🌟, Bilbao 🌟, Marín 🌟

### 3.3 Flag Filter
- **Default Flags**: Malta (MT), Liberia (LR), Marshall Islands (MH)
- **Show**: Flag emoji + country name + vessel count

### 3.4 Additional Filters
1. Search by vessel name or IMO (real-time)
2. Filter by Vessel Type (dropdown)
3. Filter by Source (All / Live Today / History Only)

### 3.5 Vessel Table
**Columns**: ☐ | ETA | Vessel | Flag | Type | Port | From | GT | DWT | 🔗
**Sortable**: All columns (click header)
**Default Sort**: ETA ascending
**Styling**: 
- Live vessels: Amber ETA
- Historical: Faded
- Live vessels >30 days old: Marked as stale

---

## 4. Inspection Request Generator (CRITICAL)

### 4.1 Message Format (FIXED - DO NOT CHANGE)
```
Dear Colleagues
Good day
Please be informed that the following vessels are scheduled to one of 
ports within my coverage, in case needed it could be a good opportunity 
to arrange attendance :

[VESSEL LIST]

Best regards
Capt. Gitlevych Illya
Flag State Inspector
Tel: +34 603 730 040 (WhatsApp)
E-mail: gitlevych.ilya@gmail.com
LinkedIn: https://www.linkedin.com/in/gitlevych/
```

### 4.2 Vessel List Format
```
Vessel Name - IMO - Port - Date
```

**Examples**:
```
Star Sky - 9399105 - Bilbao - 5-Mar-2026
Sozon - 94001922 - Santander - 18-Mar-2026
Green Warrior - 9514169 - Coruna - 6-Mar-2026
JY LAKE - 9845257 - Marin - 10-Mar-2026
Kerkyra I - 1026013 - Gijon - 27-Mar-2026
```

### 4.3 User Workflow
1. Select vessels (checkboxes)
2. Counter shows "N vessels selected"
3. Click "📧 Inspection Request" button
4. Modal dialog opens with message
5. Two buttons:
   - **📋 Copy to Clipboard**: Copies message text
   - **No per-flag splitting**: All vessels in ONE message

### 4.4 Requirements
- ✅ One combined message (NOT per-flag)
- ✅ Date format: DD-Mon-YYYY (5-Mar-2026)
- ✅ IMO placeholder if missing: "????"
- ✅ No automatic sending (user sends manually)

---

## 5. Database Requirements

### 5.1 Storage
- **File**: `fsi_vessels_db.json`
- **Format**: JSON
- **Persistence**: 30-day rolling window
- **Purpose**: Historical tracking

### 5.2 Cleanup
- **Manual**: "🗑 >30d" button removes old records
- **API Endpoint**: `/api/clearold`

---

## 6. API Endpoints

### Fetch Endpoints
- `GET /api/barcelona` — Barcelona arrivals (CSV/JSON, 30s timeout)
- `GET /api/bilbao` — Bilbao arrivals + IMO (25s timeout)
- `GET /api/marin` — Marín arrivals (20s timeout)
- `GET /api/port?vf=CODE&pid=ID&pname=NAME` — VesselFinder (15s timeout)

### Database Endpoints
- `GET /api/history` — Full database
- `GET /api/clearold` — Delete >30 days old

### Frontend
- `GET /` or `/index.html` → Dashboard

---

## 7. Technical Requirements

### 7.1 Stack
- **Language**: Python 3.11+
- **Framework**: Standard library `http.server` (NO external deps)
- **Port**: 8090 (local), configurable via PORT env var
- **Host**: 0.0.0.0 (accept external)
- **CORS**: Enabled

### 7.2 Frontend
- Vanilla HTML/CSS/JS (NO frameworks)
- Single-page app
- Local storage for preferences
- Mobile responsive

### 7.3 Performance
- Dashboard load: <2s
- Barcelona: ~3s
- Bilbao (w/ IMO): ~8s
- Marín: ~2s
- VF per port: ~2s
- Total refresh: ~20-25s
- Search/filter: <100ms

---

## 8. Cloud Deployment

### 8.1 Supported Platforms
1. **Render.com** (Recommended) — Free tier, auto-deploy
2. **Railway.app** (Easiest) — Free tier, one-click
3. **Heroku** — Paid tier required

### 8.2 Configuration
- **Procfile**: `web: python fsi_monitor_fixed.py`
- **requirements.txt**: Empty (stdlib only)
- **runtime.txt**: `python-3.11.8`
- **Env Variables**: PORT (auto-set by cloud)

### 8.3 Database on Cloud
- Location: `/tmp/fsi_vessels_db.json` (ephemeral)
- Resets on app restart
- Note: Not persistent (acceptable for this use case)

---

## 9. Success Criteria ✅

- ✅ All 4 data sources working
- ✅ Barcelona returns 100+ vessels
- ✅ Bilbao includes IMO for all vessels
- ✅ Marín returns ~8 vessels
- ✅ VesselFinder works for all 10 secondary ports
- ✅ Message template generates correctly
- ✅ No external dependencies
- ✅ Cloud deployable
- ✅ Mobile responsive
- ✅ <2s dashboard load

---

## 10. Change Management Protocol

**IMPORTANT - PROCESS FOR ALL CHANGES**:

1. **User** requests requirement change
2. **Developer** updates PRD first (this document)
3. **Developer** implements code changes to match PRD
4. **All work flows from PRD as source of truth**

### Pending Changes
- *(none at this time)*

---

## 11. Author & Contact

**Owner**: Capt. Gitlevych Illya
**Role**: Flag State Inspector, Cantabrian Region
**Email**: gitlevych.ilya@gmail.com
**Phone**: +34 603 730 040 (WhatsApp)
**LinkedIn**: https://www.linkedin.com/in/gitlevych/

**Document Status**: ✅ ACTIVE AND APPROVED
**Last Updated**: 2026-03-17
**Review Frequency**: On-demand (when requirements change)

