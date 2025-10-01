from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

def stamp(output_pdf, text, qr_png=None):
    c = canvas.Canvas(output_pdf, pagesize=A4)
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, 20*mm, text)
    if qr_png:
        c.drawImage(qr_png, 160*mm, 10*mm, width=30*mm, height=30*mm, preserveAspectRatio=True)
    c.showPage()
    c.save()
