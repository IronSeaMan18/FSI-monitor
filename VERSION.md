# FSI Monitor — VERSION LOG
Current: v3.6.0

## v3.6.0 — Flag toggle + VF supplement
1. Flag filter = clickable MT/LR/MH toggle chips with live counts + "All 3" reset.
2. Ferrol + San Ciprián query ShipNext AND VesselFinder, merge by IMO (catch missed vessels).
   (VF supplement only works when VF reachable — blocked from Render IP currently.)
localStorage key: fsi11

## Data findings
- ANJI FOREVER: IMO 1021415, Liberia, Vehicles Carrier (PCTC), built 2025. New 7-digit IMO.
- ENERGOS MARIA (9320374) + PRINCESS (9253715): LNG Tankers, Marshall Islands. IGC Code.
- Vilagarcía not in ShipNext (VF-only). Ferrol PA needs login.

## KNOWN ISSUE (unresolved from v3.5.x)
VesselFinder blocks Render's datacenter IP (all UAs, all paths). Flag resolution
and VF-only ports (Vilagarcía) fail from cloud. Needs client-side or local-resolver
solution. ShipNext-covered ports work; Bilbao (PA, Googlebot UA) works.

## Working data sources from Render
- ShipNext planned-vessels (vessel list + IMO, no flag) ✓
- Bilbao PA via Googlebot UA (vessel list + flag) ✓
- VesselFinder — BLOCKED ✗
