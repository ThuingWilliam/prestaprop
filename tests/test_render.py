import os
import sys
# Add current directory to path
sys.path.append(os.getcwd())

from flask import Flask, render_template_string, session
from database import SessionLocal
from models import Prestamo, Usuario, RolUsuario
import jinja2

# Mock Flask app for rendering
app = Flask(__name__)
app.secret_key = 'test'

def test_render():
    db = SessionLocal()
    try:
        # Get specific loan
        prestamo = db.query(Prestamo).filter(Prestamo.numero_prestamo == 'PRE-2024-001').first()
        if not prestamo:
            print("ERROR: Loan not found")
            return

        # Read template file
        with open('templates/ver_prestamo.html', 'r', encoding='utf-8') as f:
            template_content = f.read()

        # Extraction of the financial container
        # We search specifically for the rendered values
        start_tag = '<!-- Resumen Financiero Maestría -->'
        end_tag = '<!-- Ficha Técnica de Apoyo -->'
        
        start_idx = template_content.find(start_tag)
        limit_idx = template_content.find(end_tag, start_idx)
        
        if start_idx != -1 and limit_idx != -1:
            fragment = template_content[start_idx:limit_idx]
            
            with app.app_context():
                try:
                    rendered = render_template_string(fragment, prestamo=prestamo, session={'rol': 'ADMINISTRADOR'})
                    print("--- RENDERED FRAGMENT START ---")
                    print(rendered)
                    print("--- RENDERED FRAGMENT END ---")
                    
                    # Sanity check for data in HTML
                    cap_val = "{:,.2f}".format(prestamo.monto_capital)
                    paid_val = "{:,.2f}".format(prestamo.total_pagado)
                    
                    if cap_val in rendered:
                        print(f"SUCCESS: Capital {cap_val} rendered correctly")
                    else:
                        print(f"FAILURE: Expected capital {cap_val} not found in HTML")
                        
                    if paid_val in rendered:
                        print(f"SUCCESS: Total Paid {paid_val} rendered correctly")
                    else:
                        print(f"FAILURE: Expected paid {paid_val} not found in HTML")
                except Exception as e:
                    print(f"RENDER ERROR: {e}")
        else:
            print(f"ERROR: Could not find markers. Start: {start_idx}, End: {limit_idx}")

    finally:
        db.close()

if __name__ == "__main__":
    test_render()
