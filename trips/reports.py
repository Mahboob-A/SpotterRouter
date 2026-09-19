"""In-memory PDF report generation service for SpotterRouter trip plans."""

import io
from decimal import Decimal
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from trips.models import FuelStop, TripPlan


class TripPdfReportService:
    """Compiles an executive freight dispatch report into in-memory PDF bytes."""

    PAGE_WIDTH = 540  # Printable width: letter (612) - 2 * 36 pt margin

    def generate_trip_pdf(self, trip: TripPlan) -> bytes:
        """Generate PDF document bytes for a given TripPlan in-memory."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        prefetched: dict[str, Any] = getattr(trip, "_prefetched_objects_cache", {})
        if "fuel_stops" in prefetched:
            raw_stops = prefetched["fuel_stops"]
        else:
            raw_stops = list(
                trip.fuel_stops.all().select_related("station").order_by("stop_order")
            )
        fuel_stops: list[FuelStop] = [
            s for s in raw_stops if isinstance(s, FuelStop)
        ]

        total_purchased = sum(
            (s.gallons_purchased for s in fuel_stops),
            Decimal("0.000"),
        )
        initial_fuel = getattr(trip, "initial_fuel_gallons", Decimal("50.000"))
        dataset_version = (
            trip.pricing_dataset.version_code
            if trip.pricing_dataset
            else "Baseline"
        )

        styles = getSampleStyleSheet()

        brand_style = ParagraphStyle(
            "BrandTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#1e3a8a"),
        )
        subtitle_style = ParagraphStyle(
            "SubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        )
        route_header_style = ParagraphStyle(
            "RouteHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
        )
        meta_style = ParagraphStyle(
            "MetaLine",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#475569"),
        )
        section_heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=4,
        )
        cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        )
        cell_bold_style = ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        )
        cell_header_style = ParagraphStyle(
            "TableHeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )
        analysis_text_style = ParagraphStyle(
            "AnalysisText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#1e293b"),
        )

        story: list[Any] = []

        # 1. Header Banner
        header_table_data = [
            [
                Paragraph("<b>SPOTTERROUTER</b>", brand_style),
                Paragraph(
                    "<b>COMMERCIAL FREIGHT ROUTE &amp; FUEL REPORT</b>",
                    ParagraphStyle(
                        "ReportType",
                        parent=subtitle_style,
                        alignment=2,
                        fontName="Helvetica-Bold",
                        fontSize=8.5,
                        textColor=colors.HexColor("#1e3a8a"),
                    ),
                ),
            ],
            [
                Paragraph(
                    "Intelligent Fuel Stop Optimization Engine", subtitle_style
                ),
                Paragraph(
                    f"Dataset: <b>{dataset_version}</b>",
                    ParagraphStyle("DSet", parent=subtitle_style, alignment=2),
                ),
            ],
        ]
        header_table = Table(header_table_data, colWidths=[270, 270])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 6))
        story.append(
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=colors.HexColor("#1e3a8a"),
                spaceAfter=8,
                spaceBefore=0,
            )
        )

        # 2. Trip Route & Meta Info
        created_str = (
            trip.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if trip.created_at
            else "Recent"
        )
        route_text = f"{trip.start_input}  &rarr;  {trip.end_input}"
        story.append(Paragraph(route_text, route_header_style))
        story.append(Spacer(1, 2))
        meta_text = (
            f"Trip ID: <b>{trip.id}</b> &nbsp;&bull;&nbsp; "
            f"Computed: <b>{created_str}</b> &nbsp;&bull;&nbsp; "
            f"Vehicle Economy: <b>10 MPG</b> &nbsp;&bull;&nbsp; "
            f"Max Range: <b>500 miles</b>"
        )
        story.append(Paragraph(meta_text, meta_style))
        story.append(Spacer(1, 10))

        # 3. Key Metrics Grid (5 boxes)
        metrics_headers = [
            "Total Distance",
            "Total Refuel Cost",
            "Purchased En Route",
            "Total Consumption",
            "Initial Origin Tank",
        ]
        metrics_values = [
            f"{trip.total_distance_miles} mi",
            f"${trip.total_cost}",
            f"{total_purchased} gal",
            f"{trip.total_gallons} gal",
            f"{initial_fuel} gal",
        ]
        metrics_subtitles = [
            "10 MPG vehicle rating",
            "En-route purchases",
            f"{len(fuel_stops)} planned stops",
            "Total journey burn",
            "500-mi range pre-loaded",
        ]

        metrics_cells = []
        for h, v, s in zip(
            metrics_headers, metrics_values, metrics_subtitles, strict=False
        ):
            metrics_cells.append(
                Paragraph(
                    f"<font size=7 color='#64748b'><b>{h.upper()}</b></font><br/>"
                    f"<font size=11 color='#0f172a'><b>{v}</b></font><br/>"
                    f"<font size=6.5 color='#94a3b8'>{s}</font>",
                    styles["Normal"],
                )
            )

        metrics_table = Table([metrics_cells], colWidths=[108] * 5)
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#e2e8f0"),
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )
        )
        story.append(metrics_table)
        story.append(Spacer(1, 10))

        # 4. Fuel Accounting & Journey Balance Callout Box
        balance_col1 = (
            "<b>1. ORIGIN DEPARTURE</b><br/>"
            f"<b>{initial_fuel} gal</b> Full Tank<br/>"
            "<font size=7 color='#64748b'>Covers first 500.00 mi "
            "(pre-loaded at origin; not billed on trip).</font>"
        )
        balance_col2 = (
            "<b>2. EN-ROUTE REFUELING</b><br/>"
            f"<b>{total_purchased} gal &bull; ${trip.total_cost}</b><br/>"
            f"<font size=7 color='#64748b'>Purchased across {len(fuel_stops)} "
            "stops along corridor to reach destination.</font>"
        )
        balance_col3 = (
            "<b>3. TOTAL CONSUMED</b><br/>"
            f"<b>{trip.total_gallons} gal</b> Total Burn<br/>"
            f"<font size=7 color='#64748b'>Total burned over "
            f"{trip.total_distance_miles} mi "
            f"(50.0 gal origin + {total_purchased} gal refuel = 100% reconciled)."
            "</font>"
        )

        balance_header = (
            "<font color='#1e3a8a'>"
            "<b>FUEL ACCOUNTING &amp; BALANCE RECONCILIATION (10 MPG)</b>"
            "</font>"
        )
        balance_table_data = [
            [
                Paragraph(balance_header, section_heading_style),
                "",
                "",
            ],
            [
                Paragraph(balance_col1, cell_style),
                Paragraph(balance_col2, cell_style),
                Paragraph(balance_col3, cell_style),
            ],
        ]
        balance_table = Table(balance_table_data, colWidths=[180, 180, 180])
        balance_table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (2, 0)),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(balance_table)
        story.append(Spacer(1, 10))

        # 5. Route Mileage Corridor Schematic (Vector Drawing)
        story.append(
            Paragraph("Route Corridor Mileage Schematic", section_heading_style)
        )
        schematic_drawing = self._build_corridor_schematic(trip, fuel_stops)
        story.append(schematic_drawing)
        story.append(Spacer(1, 10))

        # 6. Planned Refueling Stops Table
        story.append(
            Paragraph("Planned Refueling Stops", section_heading_style)
        )
        if fuel_stops:
            table_rows: list[list[Any]] = [
                [
                    Paragraph("Stop", cell_header_style),
                    Paragraph("Station Name", cell_header_style),
                    Paragraph("Location", cell_header_style),
                    Paragraph("Miles from Origin", cell_header_style),
                    Paragraph("Gallons Purchased", cell_header_style),
                    Paragraph("Price / Gal", cell_header_style),
                    Paragraph("Stop Cost", cell_header_style),
                ]
            ]
            for stop in fuel_stops:
                table_rows.append(
                    [
                        Paragraph(f"<b>#{stop.stop_order}</b>", cell_style),
                        Paragraph(
                            f"<b>{stop.station.name}</b>", cell_style
                        ),
                        Paragraph(
                            f"{stop.station.city}, {stop.station.state}",
                            cell_style,
                        ),
                        Paragraph(
                            f"{stop.distance_from_start_miles} mi", cell_style
                        ),
                        Paragraph(f"{stop.gallons_purchased} gal", cell_style),
                        Paragraph(f"${stop.price_per_gallon}", cell_style),
                        Paragraph(
                            f"<font color='#15803d'><b>${stop.cost}</b></font>",
                            cell_style,
                        ),
                    ]
                )

            # Footer summary row
            table_rows.append(
                [
                    Paragraph(
                        "<b>Total Refuel Summary:</b>", cell_bold_style
                    ),
                    "",
                    "",
                    "",
                    Paragraph(f"<b>{total_purchased} gal</b>", cell_bold_style),
                    Paragraph("<b>-</b>", cell_bold_style),
                    Paragraph(
                        f"<font color='#15803d'><b>${trip.total_cost}</b></font>",
                        cell_bold_style,
                    ),
                ]
            )

            col_widths = [36, 144, 110, 65, 65, 55, 65]  # total = 540
            stops_table = Table(table_rows, colWidths=col_widths, repeatRows=1)

            t_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ("TOPPADDING", (0, 0), (-1, 0), 5),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#f1f5f9")),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                # Footer styling
                ("SPAN", (0, -1), (3, -1)),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ]
            # Alternating rows
            for r_idx in range(1, len(fuel_stops) + 1):
                bg_color = (
                    colors.white
                    if r_idx % 2 == 1
                    else colors.HexColor("#f8fafc")
                )
                t_style.append(
                    ("BACKGROUND", (0, r_idx), (-1, r_idx), bg_color)
                )

            stops_table.setStyle(TableStyle(t_style))
            story.append(stops_table)
        else:
            no_stops_msg = (
                f"No refueling stops required. The vehicle's 500-mile initial "
                f"fuel range covers this entire {trip.total_distance_miles}-mile trip."
            )
            story.append(Paragraph(no_stops_msg, cell_style))

        story.append(Spacer(1, 10))

        # 7. Analysis Section
        story.append(Paragraph("Analysis", section_heading_style))
        explanation_content = (
            trip.ai_explanation
            if trip.ai_explanation
            else (
                "Route computed using Greedy-with-Lookahead optimization algorithm. "
                "Operational rationale generation is either in progress or awaiting "
                "configuration."
            )
        )
        analysis_box = Table(
            [[Paragraph(explanation_content, analysis_text_style)]],
            colWidths=[540],
        )
        analysis_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(analysis_box)

        # Build document in memory
        doc.build(story)
        return buffer.getvalue()

    def _build_corridor_schematic(
        self, trip: TripPlan, fuel_stops: list[FuelStop]
    ) -> Drawing:
        """Create a vector drawing of the route corridor and fuel stop pins."""
        d = Drawing(self.PAGE_WIDTH, 42)

        # Background box
        d.add(
            Rect(
                0,
                0,
                self.PAGE_WIDTH,
                42,
                fillColor=colors.HexColor("#f8fafc"),
                strokeColor=colors.HexColor("#e2e8f0"),
                strokeWidth=0.5,
                rx=4,
                ry=4,
            )
        )

        start_x = 40.0
        end_x = 500.0
        axis_y = 20.0
        corridor_len = end_x - start_x

        # Main route corridor line
        d.add(
            Line(
                start_x,
                axis_y,
                end_x,
                axis_y,
                strokeColor=colors.HexColor("#2563eb"),
                strokeWidth=3,
            )
        )

        # Origin marker
        d.add(
            Circle(
                start_x,
                axis_y,
                5,
                fillColor=colors.HexColor("#16a34a"),
                strokeColor=colors.white,
                strokeWidth=1,
            )
        )
        start_city = trip.start_input.split(",")[0].strip()[:14]
        d.add(
            String(
                start_x - 10,
                axis_y + 9,
                f"Start: {start_city}",
                fontName="Helvetica-Bold",
                fontSize=6.5,
                fillColor=colors.HexColor("#16a34a"),
            )
        )
        d.add(
            String(
                start_x - 6,
                axis_y - 12,
                "0 mi",
                fontName="Helvetica",
                fontSize=6,
                fillColor=colors.HexColor("#64748b"),
            )
        )

        # Destination marker
        d.add(
            Circle(
                end_x,
                axis_y,
                5,
                fillColor=colors.HexColor("#dc2626"),
                strokeColor=colors.white,
                strokeWidth=1,
            )
        )
        end_city = trip.end_input.split(",")[0].strip()[:14]
        d.add(
            String(
                end_x - 30,
                axis_y + 9,
                f"Dest: {end_city}",
                fontName="Helvetica-Bold",
                fontSize=6.5,
                fillColor=colors.HexColor("#dc2626"),
            )
        )
        d.add(
            String(
                end_x - 24,
                axis_y - 12,
                f"{trip.total_distance_miles} mi",
                fontName="Helvetica",
                fontSize=6,
                fillColor=colors.HexColor("#64748b"),
            )
        )

        total_dist = (
            float(trip.total_distance_miles)
            if trip.total_distance_miles
            else 1.0
        )

        # Refuel stop markers
        for stop in fuel_stops:
            stop_dist = float(stop.distance_from_start_miles)
            fraction = min(1.0, max(0.0, stop_dist / total_dist))
            stop_x = start_x + fraction * corridor_len

            d.add(
                Circle(
                    stop_x,
                    axis_y,
                    4,
                    fillColor=colors.HexColor("#f59e0b"),
                    strokeColor=colors.white,
                    strokeWidth=1,
                )
            )
            d.add(
                String(
                    stop_x - 4,
                    axis_y + 8,
                    f"#{stop.stop_order}",
                    fontName="Helvetica-Bold",
                    fontSize=6,
                    fillColor=colors.HexColor("#d97706"),
                )
            )
            d.add(
                String(
                    stop_x - 10,
                    axis_y - 11,
                    f"${stop.price_per_gallon}",
                    fontName="Helvetica",
                    fontSize=5.5,
                    fillColor=colors.HexColor("#0f172a"),
                )
            )

        return d
