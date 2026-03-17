# Getting Started - FSI Vessel Arrival Monitor v4

Welcome to Project1! This guide will help you understand the project structure and how to use it.

---

## 📋 What is This Project?

FSI Vessel Arrival Monitor is a professional web dashboard for monitoring vessel arrivals at Spanish ports (Cantabrian & Galicia regions + Barcelona). It tracks over 200+ vessels in real-time and helps Flag State Inspectors plan inspection visits.

**Current Status**: ~70% complete | ⚠️ Critical features pending implementation

---

## 📂 Project Files Overview

### Essential Documents
| File | Purpose | Read First? |
|------|---------|-------------|
| **PRD.md** | Complete specification (v4.0) | ✅ YES - Start here |
| **CODE_VERIFICATION_REPORT.md** | What's working & what's missing | ✅ YES - Then read this |
| **fsi_monitor.py** | Main Python application | If implementing features |
| **README.md** | Setup & feature guide | For deployment |
| **PROJECT_STRUCTURE.md** | Technical architecture | For understanding layout |
| **GETTING_STARTED.md** | This file | Quick orientation |

---

## 🚀 Quick Start (Local)

### Step 1: Prerequisites
```bash
# Verify you have Python 3.11+
python3 --version
# Output should be: Python 3.11.x or higher
```

### Step 2: Run the App
```bash
cd /Users/illyagitlevych/Desktop/Project1
python3 fsi_monitor.py
```

**Expected output:**
```
╔═══════════════════════════════════════════════════════════╗
║  ⚓ FSI Vessel Arrival Monitor v3                          ║
║  Bilbao PA + Barcelona OD + Marín PA + VesselFinder        ║
║                                                            ║
║  Dashboard:  http://localhost:8090                         ║
║  Database:   fsi_vessels_db.json                           ║
║  Tracked:    0 vessels (on first run)                      ║
║  Binding:    0.0.0.0:8090                                  ║
║                                                            ║
║  Press Ctrl+C to stop                                      ║
╚═══════════════════════════════════════════════════════════╝
```

Browser will open automatically to: **http://localhost:8090**

### Step 3: Use the Dashboard
1. **Select Ports**: Click ports on the left (default: 12 ports selected)
2. **Select Flags**: Click flag buttons (default: MT, LR, MH)
3. **Search**: Type vessel name or IMO number
4. **View Results**: See matching vessels in the table
5. **Export**: Click "↓ CSV" to download data
6. **Generate Message**: Select vessels with checkboxes, click "📧 Combined Inspection Request"

### Step 4: Stop the App
```bash
# Press Ctrl+C in terminal
Press Ctrl+C to stop
Stopped.
```

---

## 📊 Understanding the Dashboard

### Top Bar
- **● LIVE + DB**: Shows app is pulling from current data + 30-day history
- **Last Updated**: Timestamp of last data refresh
- **↻ Refresh Button**: Manually fetch latest vessel data (takes ~25 seconds)
- **↓ CSV Button**: Export filtered results as CSV

### Statistics Cards
Shows 5 metrics:
- **Matched**: Total vessels matching your filters
- **Live Today**: New vessels from today's fetch
- **History**: Vessels from database (up to 30 days old)
- **Direct PA**: From Bilbao/Barcelona/Marín direct sources
- **VesselFinder**: From VesselFinder scraping

### Port Selector
- Shows all 12 ports grouped by region:
  - **Cantabrian**: Gijón, Avilés, Santander, Bilbao, Pasajes, Bayonne
  - **Galicia**: San Ciprián, Ferrol, A Coruña, Marín, Vilagarcía, Vigo
  - **Mediterranean**: Barcelona
- 🌟 = Direct data source (more reliable)
- Numbers = Vessels from that port matching your filters

### Flag Filter
- Shows 26 maritime flags
- Default: Malta 🇲🇹, Liberia 🇱🇷, Marshall Islands 🇲🇭
- Click to add/remove flags
- Numbers = Vessels under each flag

### Vessel Table
**Columns**:
1. ☐ - Checkbox for selection
2. ETA - Arrival date/time (amber for live, faded for old)
3. Vessel - Ship name + IMO number
4. Flag - Country flag emoji + code
5. Type - Bulk Carrier, Container, etc.
6. Port - Destination port
7. From - Origin port
8. GT - Gross tonnage
9. DWT - Deadweight tonnage
10. 🔗 - Link to VesselFinder

### Selection Bar
- Appears when you check vessel checkboxes
- Shows count of selected vessels
- "📧 Combined Inspection Request" button
- Pre-fills message for you to send

---

## 💌 Generating Inspection Requests

### How it Works
1. **Select vessels** using checkboxes (can select multiple)
2. **Click** "📧 Combined Inspection Request"
3. **Copy message** or **send via email**

### Current Format (TO BE FIXED)
```
Dear Colleagues
Good day

Please be informed that the following vessels are scheduled to
one of ports within my coverage, in case needed it could be a
good opportunity to arrange attendance :

Star Sky - 9399105 - Bilbao - 5-Mar-2026
Sozon - 94001922 - Santander - 18-Mar-2026
Green Warrior - 9514169 - A Coruña - 6-Mar-2026

Best regards
Capt. Gitlevych Illya
Flag State Inspector
Tel: +34 603 730 040 (WhatsApp)
E-mail: gitlevych.ilya@gmail.com
LinkedIn: https://www.linkedin.com/in/gitlevych/
```

### Email Recipients (Pre-configured)
- **Malta 🇲🇹**: maritime.surveys@transport.gov.mt
- **Liberia 🇱🇷**: inspection@liscr.com
- **Marshall Islands 🇲🇭**: inspections@register-iri.com

---

## 📁 Database

### File Location
```
/Users/illyagitlevych/Desktop/Project1/fsi_vessels_db.json
```

### Purpose
- Stores 30-day rolling history of all vessels
- Automatically updated on each refresh
- Used to show historical data even when sources go down

### Cleanup
- **Manual**: Click "🗑 >30d" in database bar
- **Automatic**: Old records auto-removed on refresh
- Keeps database size manageable

### Structure
```json
{
  "vessels": {
    "9399105_ESBIO": {
      "imo": "9399105",
      "name": "Star Sky",
      "portId": "ESBIO",
      ...
    }
  },
  "meta": {
    "runs": 42,
    "lastRun": "2026-03-17T13:00:00"
  }
}
```

---

## 🌐 Cloud Deployment

### Option 1: Render.com (Recommended)
```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Initial commit"
git push origin main

# 2. Go to https://render.com
# 3. Create new "Web Service"
# 4. Connect GitHub repo
# 5. Runtime: Python 3.11
# 6. Build: automatic (Procfile detected)
# 7. Deploy
```

**Result**: App runs 24/7, accessible via URL

### Option 2: Railway.app (Easiest)
```bash
# 1. Push to GitHub
# 2. Go to https://railway.app
# 3. Create new project → GitHub
# 4. Select Project1 repo
# 5. Auto-configures from Procfile
# 6. Deploy
```

### Option 3: Heroku (Paid)
```bash
heroku login
heroku create my-fsi-monitor
git push heroku main
heroku logs --tail
```

---

## 🔍 Data Sources

### Barcelona (✅ WORKING)
- **Type**: CSV Open Data
- **Update**: Real-time
- **Vessels**: 100+
- **Coverage**: 7 days ahead
- **Issue**: Only CSV, no JSON fallback implemented

### Bilbao (✅ WORKING)
- **Type**: HTML scraping
- **Update**: Real-time
- **Vessels**: 68
- **Coverage**: 3 weeks
- **Feature**: IMO lookup via VesselFinder
- **Note**: Takes ~8 seconds due to IMO lookups

### Marín (✅ WORKING)
- **Type**: HTML scraping
- **Update**: Real-time
- **Vessels**: 8
- **Coverage**: 10 days

### VesselFinder (✅ WORKING)
- **Type**: Web scraping
- **Update**: ~2 hours
- **Vessels**: 10 per port
- **Ports**: All other Spanish ports

---

## ⚠️ Known Issues (From Verification)

### Critical (Blocks Production)
1. **Procfile filename** - FIXED ✅ in Project1
2. **Missing daily email feature** - ❌ NOT IMPLEMENTED
3. **Message format wrong** - ⚠️ SPLITS BY FLAG (should be single message)

### High Priority
- Barcelona fallback logic (JSON → CSV) not implemented
- IMO lookup not cached
- Date format doesn't match spec (needs DD-Mon-YYYY)

### Low Priority
- Version says v3, should be v4.0
- Some timeout values slightly off

**Full details**: Read `CODE_VERIFICATION_REPORT.md`

---

## 🛠️ What to Implement Next

### Priority 1: Daily Email Feature (⭐ Core)
```
Required:
- Automatic send at 6:00 AM every day
- Filter: Cantabria + Galicia regions ONLY
- Filter: LR, MT, MH flags ONLY
- Send even if 0 vessels match
- Date format: DD-Mon-YYYY
```

### Priority 2: Fix Message Format
```
Current: Splits into separate messages per flag
Required: Single combined message for all vessels
```

### Priority 3: Barcelona Fallback
```
Current: Only uses CSV
Required: Try JSON API first, fallback to CSV
```

### Priority 4: Performance
```
Add IMO lookup caching (in-memory dict)
Currently ~1-2 sec per Bilbao vessel
```

---

## 📚 File Reading Order

1. **Start here**: This file (GETTING_STARTED.md)
2. **Then read**: PRD.md (sections 1-4 for features)
3. **Then read**: CODE_VERIFICATION_REPORT.md (understand gaps)
4. **If deploying**: README.md (deployment guides)
5. **If developing**: fsi_monitor.py (source code)
6. **For architecture**: PROJECT_STRUCTURE.md

---

## 💻 Useful Commands

```bash
# Navigate to project
cd /Users/illyagitlevych/Desktop/Project1

# Run locally
python3 fsi_monitor.py

# Check Python version
python3 --version

# List files
ls -la

# View Procfile
cat Procfile

# View requirements
cat requirements.txt

# View database (if exists)
cat fsi_vessels_db.json | python3 -m json.tool

# Test specific port
curl http://localhost:8090/api/barcelona
```

---

## 🔗 Important Links

- **PO Email**: gitlevych.ilya@gmail.com
- **PO Phone**: +34 603 730 040 (WhatsApp)
- **PO LinkedIn**: https://www.linkedin.com/in/gitlevych/

### Data Source URLs
- Barcelona: https://opendatapre.portdebarcelona.cat
- Bilbao: https://www.bilbaoport.eus/en/vessel-activity/scheduled-calls/
- Marín: https://www.apmarin.com/es/paginas/buques_esperados
- VesselFinder: https://www.vesselfinder.com

---

## ❓ Troubleshooting

### "Port 8090 already in use"
```bash
# Find what's using port 8090
lsof -i :8090

# Kill it or use different port
PORT=8091 python3 fsi_monitor.py
```

### "No vessels showing"
- Check filters (ports/flags)
- Click "↻ Refresh" to fetch fresh data
- May take 25 seconds
- Check "Live Today" source filter

### "CSV export shows no data"
- Apply filters first
- At least one vessel must match
- Data must be in table to export

### "Can't connect to vessel data"
- Check internet connection
- Some sources might be down
- App continues with other sources
- History still shows old data

### Database file is large
- Click "🗑 >30d" to clean old records
- Database grows over time
- 30-day rolling window is default

---

## 🎓 Next Steps

1. **Familiarize yourself** with the dashboard (5 min)
2. **Read PRD.md** to understand requirements (15 min)
3. **Read CODE_VERIFICATION_REPORT.md** to understand gaps (10 min)
4. **Plan fixes** based on priority (section above)
5. **Implement** critical features (daily email first)
6. **Test** thoroughly before deployment
7. **Deploy** to cloud (Render/Railway recommended)

---

## ✅ Verification Checklist

Before considering the project complete, verify:
- [ ] Daily email sends at 6:00 AM
- [ ] Email filters: Cantabria/Galicia + LR/MT/MH
- [ ] Inspection message is single, not per-flag
- [ ] Date format is DD-Mon-YYYY
- [ ] Barcelona uses JSON with CSV fallback
- [ ] IMO lookups are cached
- [ ] Version updated to v4.0
- [ ] Cloud deployment tested
- [ ] All 4 data sources working

---

**Happy monitoring! 🚢⚓**

For questions or issues, contact Capt. Gitlevych Illya
