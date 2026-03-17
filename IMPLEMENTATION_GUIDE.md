# Implementation Guide - Adding More Port Data Sources

## Current Status

### ✅ What Works
- **Barcelona**: Direct CSV export from Open Data Portal (100+ vessels)
- **Bilbao**: HTML scraping + IMO lookup (68 vessels)
- **Marín**: HTML scraping (8 vessels)
- **All other ports**: VesselFinder scraping (~10 vessels due to JavaScript pagination)

### ❌ What Needs Fixing
- **Coruña**: Still limited to ~10 vessels (VesselFinder limitation)
- **Tarragona**: Just added, needs data source
- **All other ports**: Want to show more than 10 vessels

---

## Problem: Why Only 10 Vessels per Port?

### The Root Cause
VesselFinder uses **JavaScript to dynamically load** more vessels:
1. Page initially loads ~10 vessels in HTML
2. User clicks "Load More" or scrolls
3. JavaScript makes AJAX request to load next batch
4. Server-side scraper can ONLY see initial HTML (no JavaScript execution)
5. Result: Limited to 10 vessels

### Why Bilbao & Marín Don't Have This Problem
- They scrape directly from **Port Authority websites**
- Port Authority websites return **full HTML** with all vessels
- No JavaScript pagination required
- Result: All 68 vessels (Bilbao) and 8 vessels (Marín)

---

## Solution: Scrape Port Authority Websites Directly

Like we do for **Bilbao** and **Marín**, each port publishes their own expected arrivals list.

### How Bilbao Currently Works

```python
def fetch_bilbao():
    # 1. Request Bilbao Port Authority website
    req = urllib.request.Request(
        "https://www.bilbaoport.eus/en/vessel-activity/scheduled-calls/",
        headers={"User-Agent": UA}
    )
    # 2. Parse HTML table
    html = urllib.request.urlopen(req).read().decode("utf-8")
    tables = re.findall(r'<table[^>]*>(.+?)</table>', html, re.DOTALL)

    # 3. Extract vessels from table rows
    vessels = []
    for table_html in tables:
        for row in table_html.split('<tr>'):
            # Extract: name, origin, destination, ETA, flag, GT, LOA
            # Then lookup IMO number separately

    return vessels
```

### How to Replicate for Other Ports

Each port we want to add follows the same pattern:

#### **Template for New Port**

```python
def fetch_[PORT_CODE]():
    """
    Fetch vessel arrivals from [PORT_NAME]
    Example: fetch_gijon(), fetch_aviles(), fetch_santander()
    """
    try:
        # 1. Determine the port's expected arrivals URL
        url = "[PORT_WEBSITE]/expected-arrivals or /scheduled-calls or /buques-esperados"

        # 2. Request with proper User-Agent
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")

        # 3. Find tables or vessel listings
        tables = re.findall(r'<table[^>]*>(.+?)</table>', html, re.DOTALL)
        vessels = []

        # 4. Parse each table row
        for table_html in tables:
            for row in table_html.split('<tr>'):
                # Extract vessel data from HTML columns
                name = extract_name(row)       # Vessel name
                flag = extract_flag(row)       # Flag country
                origin = extract_origin(row)   # Origin port
                eta = extract_eta(row)         # Estimated Time of Arrival

                if not name: continue

                # 5. Lookup IMO (optional, like Bilbao does)
                imo = lookup_imo(name)  # Uses VesselFinder to find IMO

                vessels.append({
                    "name": name,
                    "imo": imo,
                    "flag": flag,
                    "origin": origin,
                    "eta": eta,
                    # ... other fields
                })

        return vessels
    except Exception as e:
        log(f"Error fetching [PORT]: {e}")
        return []
```

---

## Step-by-Step Guide: Adding Gijón

### 1. Find Gijón's Expected Arrivals URL

```bash
# Visit their website and look for:
# - "Buques Esperados" (Expected Vessels)
# - "Scheduled Calls"
# - "Vessel Schedule"
# - Calendar or table of arrivals

curl https://www.puertodegijón.es -A "Mozilla/5.0" | grep -i "buque\|vessel\|arrival"
```

### 2. Analyze the HTML Structure

Example of what we'd find:
```html
<table>
  <tr>
    <td>Name: Star Sky</td>
    <td>Flag: PA</td>
    <td>ETA: 2026-03-05 13:00</td>
    <td>Origin: Singapore</td>
  </tr>
</table>
```

### 3. Create Regex Patterns

Extract fields using regex (like we do for Bilbao):

```python
def extract_gijon_vessels(html):
    vessels = []

    # Example pattern: Find all table rows
    rows = re.findall(r'<tr>(.+?)</tr>', html, re.DOTALL)

    for row in rows:
        # Extract each field from the row
        name_m = re.search(r'<td>Name[^<]*:?\s*([^<]+)</td>', row, re.I)
        flag_m = re.search(r'<td>Flag[^<]*:?\s*(\w+)</td>', row, re.I)
        eta_m = re.search(r'<td>ETA[^<]*:?\s*([^<]+)</td>', row, re.I)

        if name_m:
            vessels.append({
                "name": name_m.group(1).strip(),
                "flagCode": flag_m.group(1) if flag_m else "",
                "eta": eta_m.group(1) if eta_m else "",
            })

    return vessels
```

### 4. Add to API Endpoints

In the Python HTTP handler, add:

```python
elif p.path == "/api/gijon":
    try:
        vs = fetch_gijon()  # Call our new function
        db = load_db()
        a, u = merge_into_db(db, vs, "ESGIJ", "Gijón", "GIJ-PA")
        save_db(db)
        self._json(200, {"vessels": vs, "count": len(vs), "added": a, "updated": u})
    except Exception as e:
        self._json(500, {"error": str(e), "vessels": [], "count": 0})
```

### 5. Add Frontend Integration

In the JavaScript frontend, add:

```javascript
// Add to port click handler
async function handlePortSelection(portId) {
    if (portId === "ESGIJ") {
        const res = await fetch("/api/gijon");
        const data = await res.json();
        // Process response...
    }
}
```

---

## Priority Order for Adding Ports

### 🔴 **HIGH PRIORITY** (Most traffic expected)
1. **Gijón** (ESGIJ) - Major Cantabrian port
2. **Avilés** (ESAVS) - Major Cantabrian port
3. **Santander** (ESTAN) - Major Cantabrian port
4. **Vigo** (ESVGO) - Major Galician port
5. **A Coruña** (ESCOR) - Replace VesselFinder with direct source

### 🟡 **MEDIUM PRIORITY** (Important)
6. **Tarragona** (ESTGN) - Mediterranean, recently added
7. **Ferrol** (ESFER) - Galician naval port
8. **Vilagarcía** (ESVIL) - Galician port

### 🟢 **LOW PRIORITY** (Supplementary)
9. **Pasajes** (ESPAS) - Small Cantabrian
10. **San Ciprián** (ESSCI) - Small Galician
11. **Bayonne** (FRBAY) - French port

---

## Alternative Approach: Regional Open Data APIs

If Port Authority websites don't have public data, try regional APIs:

### **Euskadi (Basque Country)**
Covers: Bilbao, Pasajes, and other Basque ports

```python
# Use OpenData Euskadi API
url = "https://opendata.euskadi.eus/api/..."
response = urllib.request.urlopen(url)
data = json.load(response)
```

### **Galicia**
Covers: A Coruña, Ferrol, Vigo, Vilagarcía, Marín

```python
# Use Galicia Open Data API
url = "https://open.xunta.gal/api/..."
response = urllib.request.urlopen(url)
data = json.load(response)
```

### **Catalonia**
Covers: Barcelona, Tarragona

```python
# Use Catalonia Open Data API
url = "https://data.gencat.cat/api/..."
response = urllib.request.urlopen(url)
data = json.load(response)
```

---

## Testing Your New Port Function

### 1. Test Locally

```python
# In Python terminal
vessels = fetch_gijon()
print(f"Found {len(vessels)} vessels in Gijón")
for v in vessels[:5]:
    print(f"  - {v['name']} ({v.get('imo', 'N/A')})")
```

### 2. Test API Endpoint

```bash
curl http://localhost:8090/api/gijon | python3 -m json.tool
```

### 3. Test in Browser

1. Go to http://localhost:8090
2. Select "Gijón" port
3. Verify data appears in table

---

## Performance Considerations

### Timeout Values
Each fetch should complete within:
- **Direct HTML scrape**: ~2-5 seconds
- **With IMO lookup**: ~5-8 seconds (like Bilbao)
- **Total for all ports**: ~20-25 seconds

### Caching
- IMO lookups are cached to avoid duplicates
- Port data is merged into 30-day database
- Old records automatically cleaned

### Rate Limiting
- Add `time.sleep(0.5)` between requests to same port
- Add User-Agent rotation if needed
- Respect robots.txt if present

---

## What We Need From You

To complete this implementation, we need:

1. **For each port**, identify:
   - ✅ Expected arrivals page URL
   - ✅ HTML table structure (table class, row format, column headers)
   - ✅ Data fields available (name, flag, ETA, origin, destination)
   - ✅ Whether data is in HTML table (scrapeable) or JavaScript-loaded

2. **Provide sample URLs** for:
   - Gijón expected arrivals
   - Avilés expected arrivals
   - Santander expected arrivals
   - Vigo expected arrivals
   - Coruña (to replace VesselFinder)
   - Tarragona

3. **Or** point us to regional open data APIs if ports don't have public data

---

## Code Template: Complete Example

Here's a complete example for adding a new port:

```python
def fetch_gijon():
    """Fetch vessel arrivals from Gijón Port Authority - Expected arrivals list"""
    try:
        # Request Gijón's expected arrivals page
        url = "https://www.puertodegijón.es/buques-esperados"  # Example URL
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")

        vessels = []

        # Find the main vessel table
        tables = re.findall(r'<table[^>]*class="vessel[^"]*"[^>]*>(.+?)</table>', html, re.DOTALL)

        if not tables:
            return vessels

        # Process first table (or iterate all)
        for table_html in tables:
            # Split by table rows
            for row in table_html.split('<tr>')[1:]:  # Skip header
                if not row.strip():
                    continue

                # Extract columns
                tds = re.findall(r'<td[^>]*>([^<]+)</td>', row)

                if len(tds) < 4:
                    continue

                name = tds[0].strip()
                flag_code = tds[1].strip().upper()
                eta = tds[2].strip()
                origin = tds[3].strip() if len(tds) > 3 else ""

                if not name:
                    continue

                # Optional: Lookup IMO using VesselFinder (like Bilbao)
                imo = lookup_imo(name) if name else ""

                # Map flag codes
                if flag_code in XMAP:
                    flag_code = XMAP[flag_code]

                vessels.append({
                    "name": name,
                    "imo": imo,
                    "flagCode": flag_code,
                    "eta": eta,
                    "origin": origin,
                })

                time.sleep(0.1)  # Slight delay between IMO lookups

        return vessels

    except Exception as e:
        log(f"Error fetching Gijón: {e}")
        return []
```

---

## Next Steps

1. **Identify Gijón's vessel data source**
   - Visit https://www.puertodegijón.es
   - Find expected arrivals/scheduled calls section
   - Note the URL and HTML structure

2. **Create `fetch_gijon()` function** using template above

3. **Add API endpoint** for `/api/gijon`

4. **Test locally** and verify data

5. **Repeat for Avilés, Santander, Vigo**

6. **For Coruña**: Either find direct source or implement headless browser solution

---

## Questions?

- **How to find port's HTML structure?** → Use browser Developer Tools (F12)
- **Port doesn't have public data?** → Check regional open data API
- **Still getting only 10 vessels?** → Port likely uses JavaScript pagination (need headless browser)
- **Need IMO lookup?** → Use `lookup_imo()` function (like Bilbao does)

---

**Ready to implement?** 🚢⚓

Provide the port URLs and HTML structures, and we'll add them to the system!

