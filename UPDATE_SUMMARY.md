# FSI Vessel Arrival Monitor v3 — Updates

## ✅ Changes Completed

### 1. **Barcelona Data Source — FIXED** ✨
**Problem:** Barcelona API returning 0 vessels
**Solution:** 
- Fixed vessel filtering to accept entries without IMO (using vessel name as fallback key)
- Extract date from ETA timestamp (format: 2026-03-21 HH:MM:SS → 2026-03-21)
- **Result:** Now fetching **118 vessels** from Barcelona Open Data API

```python
# Old: Filtered out vessels without IMO
if not imo or imo in seen: continue

# New: Accept vessels by name if IMO missing
key = imo if imo else name.upper()
if key in seen: continue
```

---

### 2. **Bilbao IMO Lookup — ADDED** 🔍
**Requirement:** Connect vessel names + flag codes to get IMO numbers via VesselFinder

**Implementation:**
```python
def lookup_imo(vessel_name, flag_code, port_name=""):
    """Search VesselFinder for IMO by vessel name and flag"""
    # Searches: https://www.vesselfinder.com/vessels?name=...&flag=...
    # Returns IMO from first matching vessel
```

**Usage:** Bilbao vessels now get IMO numbers automatically during fetch
- Bilbao PA → Vessel Name + Flag → VesselFinder Search → IMO
- Result: Bilbao vessels now have IMO data for better tracking

---

### 3. **Inspection Request Template — UPDATED** 📧

**Old Format:** Detailed formal letter with inspectionrequirements

**New Format:** Simple, friendly notification
```
Dear Colleagues
Good day
Please be informed that the following vessels are scheduled to 
one of ports within my coverage, in case needed it could be a 
good opportunity to arrange attendance :

[Vessel List]

Best regards
Capt. Gitlevych Illya
Flag State Inspector
Tel: +34 603 730 040 (WhatsApp)
E-mail: gitlevych.ilya@gmail.com
LinkedIn: https://www.linkedin.com/in/gitlevych/
```

**Vessel List Format:**
```
Star Sky - 9399105 - Bilbao - 2026-03-05
Sozon - 9400192 - Santander - 2026-03-18
Green Warrior - 9514169 - Coruna - 2026-03-06
```

---

## 📊 Current Data Sources

| Port | Source | Vessels | Range | Notes |
|------|--------|---------|-------|-------|
| **Bilbao** | Port Authority | 68 | 3 weeks | + IMO lookup via VesselFinder |
| **Barcelona** | Open Data API | 118 | 7 days | ✅ Fixed & working |
| **Marín** | Port Authority | ~8 | 10 days | Stable |
| **Other ports** | VesselFinder | 10/port | 5 days | On demand |

---

## 🚀 Running the App

### Local
```bash
cd /Users/illyagitlevych/Desktop/"agents copy"
python3 fsi_monitor.py
# Opens http://localhost:8090
```

### Cloud (unchanged)
- Railway: Push to GitHub, auto-deploys
- Render: Free tier available
- VPS: systemd + nginx included

---

## 📝 Test Results
```
✓ Python syntax: Valid
✓ Barcelona: 118 vessels fetched (date format: YYYY-MM-DD)
✓ IMO lookup: Integrated into Bilbao fetch
✓ Message template: Updated to new format
```

---

## 📌 Next Steps (Optional)
- [ ] Add more port data sources
- [ ] Implement vessel alerts/notifications
- [ ] Add port-specific inspection templates
- [ ] Multi-language support
- [ ] Export to spreadsheet formats

