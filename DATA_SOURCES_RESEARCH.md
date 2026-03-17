# Data Sources Research - FSI Vessel Arrival Monitor

**Objective**: Find open-source data for Spanish ports to show >10 vessels per port
**Date**: 2026-03-17
**Status**: In Progress

---

## Current Data Sources

### ✅ Working Sources (Direct Data)

| Port | Source | Vessels | Method | Format |
|------|--------|---------|--------|--------|
| **Barcelona** | Open Data API | 100+ | CSV download | Open Data Portal |
| **Bilbao** | Port Authority | 68 | HTML scraping | Web scraping |
| **Marín** | Port Authority | 8 | HTML scraping | Web scraping |
| **All Others** | VesselFinder | ~10 | Web scraping | HTML table (JS pagination) |

---

## Problem Analysis

### Why VesselFinder Limited to 10 per Port?
- VesselFinder uses **JavaScript pagination** (dynamic content loading)
- Server-side scraper can only see HTML already loaded
- Client-side JavaScript loads additional rows when user scrolls/clicks "Load More"
- **Solution needed**: Find alternative sources OR use headless browser

### Why Coruña Still Shows Limited Vessels?
- VesselFinder API/pagination not accessible via static HTML
- Needs dynamic JavaScript execution to load all vessels

---

## Candidate Data Sources to Research

### 1. **Port Authority Websites (Best Source)**
Many Spanish ports publish their own expected arrival lists:

| Port | Authority | Website | Status |
|------|-----------|---------|--------|
| **Gijón** | Puerto de Gijón | https://www.puertodegijón.es | 📍 Need to check |
| **Avilés** | Puerto de Avilés | https://www.puertoaviles.com | 📍 Need to check |
| **Santander** | Puerto de Santander | https://www.puertosantander.com | 📍 Need to check |
| **Pasajes** | Puerto de Pasajes | https://www.puertodelaspasajes.es | 📍 Need to check |
| **San Ciprián** | Puerto de San Ciprián | https://www.puertodesanciprian.es | 📍 Need to check |
| **Ferrol** | Puerto de Ferrol | https://www.puertodeferrol.es | 📍 Need to check |
| **A Coruña** | Puerto de A Coruña | https://www.puertocoruna.com | 📍 Need to check |
| **Vilagarcía** | Puerto de Vilagarcía | https://www.puertovilagarcía.es | 📍 Need to check |
| **Vigo** | Puerto de Vigo | https://www.puertovigo.es | 📍 Need to check |
| **Tarragona** | Puerto de Tarragona | https://www.porttarragona.cat | 📍 Need to check |
| **Bayonne** | Port de Bayonne (FR) | https://www.bayonne-port.com | 📍 Need to check |

---

### 2. **Spanish Government Open Data Portals**

#### **a) Portal de Transparencia (GOB.ES)**
- **URL**: https://www.transparencia.gob.es
- **Coverage**: All Spanish government data
- **Status**: 📍 Need to check for port data

#### **b) Datos.gob.es** (Spanish Open Data Portal)
- **URL**: https://datos.gob.es
- **Description**: Official Spanish open data repository
- **Likely datasets**:
  - Maritime traffic data
  - Port statistics
  - Vessel movements
- **Status**: 📍 Research needed

#### **c) EUROSTAT** (EU Statistics)
- **URL**: https://ec.europa.eu/eurostat
- **Coverage**: European maritime statistics
- **Status**: ❌ Aggregate data only, not vessel-level

---

### 3. **International Maritime Data Providers**

#### **a) International Maritime Organization (IMO)**
- **GISIS Database**: https://gisis.imo.org
- **Access**: Publicly available vessel data
- **Data**: IMO numbers, flags, types, sizes
- **Limitation**: Not arrival/ETA specific
- **Status**: 📍 Could be integrated

#### **b) UN/CEFACT** (UN Centre for Trade Facilitation)
- **Coverage**: Maritime declarations
- **Status**: ❌ Enterprise/B2B only

---

### 4. **European Port Authorities Network**

#### **ESPO** (European Sea Ports Organization)
- **URL**: https://www.espo.be
- **Member Ports**: All major European ports
- **Data Sharing**: Some ports share traffic data
- **Status**: 📍 Worth investigating

---

### 5. **Vessel Traffic Service (VTS) Data**

#### **Spanish VTS Providers**
- **Costas Españolas** (Spanish Coast Guard)
  - **Authority**: Dirección General de la Marina Mercante
  - **Data**: Real-time vessel positions + ETAs
  - **Public Access**: ❓ Limited, mainly for maritime safety

---

### 6. **Real-Time Tracking Services**

#### **a) MarineTraffic**
- **Website**: https://www.marinetraffic.com
- **API**: Available (paid)
- **Data**: Real-time positions, ETAs, routes
- **Free tier**: Limited access
- **Status**: ❌ Paid service (not suitable for open-source)

#### **b) VesselFinder**
- **Website**: https://www.vesselfinder.com
- **Current**: Already using (10 vessel limit)
- **API**: Not publicly available
- **Status**: ⚠️ Current scraping approach limited

#### **c) FleetMon**
- **Website**: https://www.fleetmon.com
- **Status**: ❌ Paid service

---

### 7. **Regional/Local Port Authority Data**

#### **Basque Country (Euskadi)**
- **OpenData Euskadi**: https://opendata.euskadi.eus
- **Coverage**: Ports: Bilbao, Pasajes, Bermeo
- **Status**: 📍 Need to check API

#### **Catalonia (Catalunya)**
- **OpenData ACN**: https://data.gencat.cat
- **Coverage**: Ports: Barcelona, Tarragona, Tortosa
- **Status**: 📍 Need to check API

#### **Galicia**
- **OpenData Galicia**: https://open.xunta.gal
- **Coverage**: Ports: A Coruña, Ferrol, Vigo, Vilagarcía, Marín
- **Status**: 📍 Need to check API

---

## Strategy: Multi-Source Approach

### **Phase 1: Direct Port Authority Scraping**
Scrape individual port websites like we do for Bilbao/Marín:
- `fetch_gijón()` - Gijón Port Authority
- `fetch_avilés()` - Avilés Port Authority
- `fetch_santander()` - Santander Port Authority
- etc.

**Pros**:
- Most up-to-date data
- Full vessel lists (no limit)
- Official source

**Cons**:
- Each port has different website structure
- Requires individual scraping logic for each
- May change over time

---

### **Phase 2: Regional Open Data APIs**
Use regional open data portals:
- **Euskadi**: Bilbao, Pasajes
- **Catalonia**: Barcelona, Tarragona
- **Galicia**: A Coruña, Ferrol, Vigo, Vilagarcía, Marín

**Pros**:
- Structured API data
- Multiple ports from single source
- More stable than HTML scraping

**Cons**:
- Different API formats per region
- May require API keys
- Limited documentation

---

### **Phase 3: Headless Browser Solution** (Advanced)
If scraping isn't sufficient, use **Selenium/Puppeteer** headless browser:
- Execute JavaScript to load dynamic content
- Access VesselFinder pagination properly
- Wait for AJAX to load all vessels

**Pros**:
- Get all VesselFinder data
- More reliable scraping

**Cons**:
- Adds dependency (breaks "stdlib only" requirement)
- Slower execution
- More resource-intensive

---

## Recommended Priority

### 🟢 **Priority 1: Investigate Regional Open Data APIs**
- Easiest to implement
- No dependencies
- Covers multiple ports

### 🟡 **Priority 2: Add Port Authority Scraping**
- Gijón, Avilés, Santander (Cantabrian)
- Ferrol, Vigo (Galicia)
- Tarragona (Mediterranean)

### 🔴 **Priority 3: Headless Browser** (Only if others fail)
- Add Selenium/Puppeteer
- Get complete VesselFinder data
- Resource-heavy but effective

---

## Next Steps

1. **Check Gijón Port Website**
   ```bash
   curl https://www.puertodegijón.es | grep -i "vessel\|ship\|arrival"
   ```

2. **Check Avilés Port Website**
   ```bash
   curl https://www.puertoaviles.com | grep -i "vessel\|ship\|arrival"
   ```

3. **Check Regional APIs**
   - Test Euskadi Open Data API
   - Test Galicia Open Data API
   - Test Catalonia Open Data API

4. **Analyze Port Website HTML**
   - Identify expected arrival tables
   - Create scraping patterns
   - Test with Bilbao/Marín pattern

5. **Create Implementation Plan**
   - Add functions for each port
   - Integrate with existing API
   - Test coverage

---

## Current Blockers

- ❌ **10-vessel limit on VesselFinder**: Need alternative source
- ❌ **Coruña incomplete**: VesselFinder pagination not accessible
- ⚠️ **Tarragona not yet added**: Need to find data source
- ⚠️ **Other ports using VesselFinder only**: Limited to 10 vessels

---

## Success Criteria

- ✅ All 14 ports show 20+ vessels (or maximum available)
- ✅ No external dependencies added (keep stdlib only)
- ✅ Page load time <3 seconds with default ports
- ✅ Data updated every 20-30 minutes
- ✅ All sources documented in PRD

---

## Resources to Explore

1. **Spanish Maritime Authority**
   - https://www.mitma.gob.es (Ministry of Transport)

2. **EU Port Network**
   - https://www.easygoing-project.eu

3. **International Maritime Data**
   - https://www.unctad.org/en/pages/DTL/transparency-exchange/ShipsOnline

4. **Port Community Systems**
   - Most major ports use standardized Port Community System (PCS)
   - May expose data via APIs

---

**Status**: 🔄 Awaiting research and implementation

