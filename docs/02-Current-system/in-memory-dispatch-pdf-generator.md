# In-Memory Dispatch PDF Generator

## Commercial Dispatch Requirements
In real-world logistics, truck drivers cannot always depend on a reliable cellular connection while driving through remote interstate corridors. Fleet managers rely on commercial driver dispatch sheets that can be printed or downloaded to a tablet as a PDF before departure.

The dispatch sheet must contain:
1. Complete trip summary (Origin, Destination, Total Distance, Total Fuel Cost, Total Gallons, Expected MPG).
2. Itemized turn-by-turn refueling stops with station names, addresses, mile markers, prices, gallons, and stop costs.
3. A visual corridor schematic showing where stops occur along the trip.
4. Fuel safety disclosures and operational notes.

```text
+-----------------------------------------------------------------------+
|  SpotterRouter COMMERCIAL DRIVER DISPATCH SHEET                       |
|  Trip ID: 6b151003-f1e0-4324-8d89-fd8781ae4766                        |
+-----------------------------------------------------------------------+
|  Origin: Chicago, IL                  Total Distance: 961.45 mi       |
|  Destination: Wilmer, TX              Total Cost: $135.09             |
+-----------------------------------------------------------------------+
|  [========================== Corridor Schematic ====================] |
|  mi 0                 mi 303.7          mi 783.3          mi 961.4    |
|  Origin               [Stop #1]         [Stop #2]         Dest        |
+-----------------------------------------------------------------------+
|  Stop  | Station Name        | Location      | Miles   | Gal   | Cost |
|  #1    | HUCKS FOOD & FUEL   | Marion, IL    | 303.7mi | 28.3g | $83  |
|  #2    | Quiktrip #7900      | Texarkana, TX | 783.3mi | 1.2g  | $4   |
+-----------------------------------------------------------------------+
```

## Why In-Memory Streaming?
For this assessment, we deliberately avoided writing PDF files to local disk or spinning up external cloud storage buckets (like AWS S3 or Google Cloud Storage):
- **Zero Disk Leakage**: Generating hundreds of PDF files on local disk would slowly fill up the Docker container's storage unless complex background cleanup cron jobs were maintained.
- **Sub-Second Streaming**: Using Python's `io.BytesIO` buffer, ReportLab compiles the document directly in memory and streams the raw bytes directly into Django's `HttpResponse(buffer.getvalue(), content_type="application/pdf")`.
- **Immediate Response**: The entire PDF generation and streaming cycle takes approximately 35 milliseconds.

## Technical Architecture of `TripPdfReportService`

### 1. Vector Corridor Schematic
Instead of rasterizing a heavy web map screenshot into a raster PNG (which would require headless Chrome or Puppeteer), ReportLab draws a vector schematic directly using `reportlab.graphics.shapes.Drawing`:
- A continuous horizontal track represents the route from mile 0 to total miles.
- Green circular nodes indicate the departure origin.
- Red circular nodes mark the destination.
- Amber markers pinpoint each planned refuel stop at its proportional distance along the route.
- Crisp vector output at any zoom level with zero image compression artifacts.

### 2. Tabular Refueling Schedule
The report formats the refueling itinerary using `reportlab.platypus.Table`:
- Header styled with high-contrast corporate navy `#1e293b`.
- Alternating row backgrounds (`#ffffff` and `#f8fafc`) for readability in low-light truck cabins.
- Numeric columns right-aligned with tabular figures.
- Explicit summary row calculating total gallons and total fuel spend.

### 3. Professional Page Numbering and Canvas Decorator
A custom `NumberedCanvas` class overrides ReportLab's standard page drawing cycle. It captures the total page count dynamically so footers display:
`"Page X of Y | Generated UTC YYYY-MM-DD | SpotterRouter Dispatch Engine"`

## Preview vs Direct Download
The HTTP endpoint supports both behaviors:
- Visiting `/trips/<uuid>/pdf/` opens the PDF inline in the browser viewer so dispatchers can preview it immediately.
- Clicking the download button sends the HTTP header `Content-Disposition: attachment; filename="spotterrouter-dispatch-<uuid>.pdf"` so the browser saves it directly to the driver's device.
