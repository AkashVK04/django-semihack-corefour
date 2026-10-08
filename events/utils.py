import io
import qrcode
import datetime
from django.core.files.base import ContentFile
from django.conf import settings
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def generate_qr_code(participant, domain="http://127.0.0.1:8000"):
    """Generate QR code for participant certificate verification."""
    verify_url = f"{domain}/verify/{participant.certificate_hash}/"
    qr = qrcode.QRCode(
        version=2,
        box_size=8,
        border=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    filename = f"qr_{participant.student_id}.png"
    participant.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
    return verify_url


def generate_certificate_pdf(participant, certificate=None):
    """Generate a styled production PDF certificate using ReportLab."""
    from .models import Certificate

    if not certificate:
        certificate, created = Certificate.objects.get_or_create(
            participant=participant,
            defaults={
                'event': participant.event,
                'certificate_hash': participant.certificate_hash,
                'certificate_id': Certificate.generate_certificate_id(),
                'status': 'VALID'
            }
        )

    buffer = io.BytesIO()

    # Page setup - landscape A4
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    # --- Background canvas (clean off-white) ---
    c.setFillColorRGB(0.98, 0.98, 0.99)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # Outer decorative gold frame
    c.setStrokeColorRGB(0.72, 0.58, 0.22)  # Refined Gold
    c.setLineWidth(6)
    c.rect(24, 24, page_w - 48, page_h - 48, fill=0, stroke=1)

    # Inner subtle border
    c.setStrokeColorRGB(0.85, 0.75, 0.45)
    c.setLineWidth(1.5)
    c.rect(34, 34, page_w - 68, page_h - 68, fill=0, stroke=1)

    # Corner ornaments
    for x, y in [(42, 42), (page_w - 42, 42), (42, page_h - 42), (page_w - 42, page_h - 42)]:
        c.setFillColorRGB(0.72, 0.58, 0.22)
        c.circle(x, y, 5, fill=1, stroke=0)

    # Top Navy Banner Strip
    c.setFillColorRGB(0.06, 0.09, 0.16)  # Deep Slate Navy #0F172A
    c.rect(24, page_h - 96, page_w - 48, 56, fill=1, stroke=0)

    # Institution branding
    c.setFillColorRGB(0.95, 0.82, 0.45)  # Gold text
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_w / 2, page_h - 58, "EDUEVENT DIGITAL CERTIFICATION PLATFORM")
    c.setFillColorRGB(0.85, 0.9, 0.95)
    c.setFont("Helvetica", 9.5)
    c.drawCentredString(page_w / 2, page_h - 75, "Department of Computer Science & Engineering · SJB Institute of Technology")

    # Certificate Header
    c.setFillColorRGB(0.06, 0.09, 0.16)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(page_w / 2, page_h - 150, "CERTIFICATE OF PARTICIPATION")

    # Certificate ID Badge
    c.setFillColorRGB(0.4, 0.45, 0.55)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(page_w / 2, page_h - 172, f"Certificate ID: {certificate.certificate_id}")

    # Golden accent line
    c.setStrokeColorRGB(0.72, 0.58, 0.22)
    c.setLineWidth(1.5)
    c.line(page_w / 2 - 140, page_h - 182, page_w / 2 + 140, page_h - 182)

    # Certification text
    c.setFillColorRGB(0.25, 0.28, 0.35)
    c.setFont("Helvetica", 12)
    c.drawCentredString(page_w / 2, page_h - 212, "This certificate is proudly awarded to")

    # Participant Name
    c.setFillColorRGB(0.05, 0.12, 0.38)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(page_w / 2, page_h - 246, participant.name.upper())

    # Underline for name
    name_width = c.stringWidth(participant.name.upper(), "Helvetica-Bold", 26)
    c.setStrokeColorRGB(0.72, 0.58, 0.22)
    c.setLineWidth(1)
    c.line(page_w / 2 - name_width / 2, page_h - 253, page_w / 2 + name_width / 2, page_h - 253)

    # Student ID Subtext
    c.setFillColorRGB(0.45, 0.5, 0.6)
    c.setFont("Helvetica", 10)
    c.drawCentredString(page_w / 2, page_h - 268, f"Student ID / Roll No: {participant.student_id}")

    # Event participation context
    c.setFillColorRGB(0.25, 0.28, 0.35)
    c.setFont("Helvetica", 12)
    c.drawCentredString(page_w / 2, page_h - 292, "for active participation and successful completion of the academic event")

    # Event Title
    c.setFillColorRGB(0.06, 0.09, 0.16)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(page_w / 2, page_h - 316, f'"{participant.event.name}"')

    # Date and Venue
    c.setFillColorRGB(0.35, 0.4, 0.48)
    c.setFont("Helvetica", 10.5)
    date_str = participant.event.date.strftime("%B %d, %Y")
    c.drawCentredString(page_w / 2, page_h - 336, f"Conducted on {date_str}  ·  Venue: {participant.event.venue}")

    # Status Badges Top Right
    if certificate.status == 'REVOKED':
        c.setFillColorRGB(0.85, 0.15, 0.15)  # Red for revoked
        c.roundRect(page_w - 175, page_h - 190, 140, 28, 5, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(page_w - 105, page_h - 172, "✕ CERTIFICATE REVOKED")
    else:
        c.setFillColorRGB(0.08, 0.52, 0.28)  # Green for valid
        c.roundRect(page_w - 175, page_h - 190, 140, 28, 5, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(page_w - 105, page_h - 172, "✓ VALID CERTIFICATE")

    # Footer signature lines
    sig_y = 66
    signatures = [
        (140, "Event Coordinator"),
        (page_w / 2, "Head of Department"),
        (page_w - 140, "Principal / Authority"),
    ]

    for sx, label in signatures:
        c.setStrokeColorRGB(0.72, 0.58, 0.22)
        c.setLineWidth(1)
        c.line(sx - 65, sig_y + 20, sx + 65, sig_y + 20)
        c.setFillColorRGB(0.2, 0.25, 0.35)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(sx, sig_y + 8, label)

    # Verification Footer Bar
    c.setFillColorRGB(0.06, 0.09, 0.16)
    c.rect(24, 24, page_w - 48, 28, fill=1, stroke=0)

    c.setFillColorRGB(0.8, 0.85, 0.95)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(
        page_w / 2,
        34,
        f"Official Verification Hash: {certificate.certificate_hash}  |  Public Verification: /verify/{certificate.certificate_hash}/"
    )

    c.save()
    buffer.seek(0)
    return buffer
