from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from models.enums import FrecuenciaPago, EstadoCuota, EstadoPrestamo, MetodoPago
from models.prestamo import Prestamo, CuotaProgramada
from models.pago import Pago, AplicacionPago

PERIODOS_POR_ANO = {
    FrecuenciaPago.SEMANAL:   Decimal("52"),
    FrecuenciaPago.QUINCENAL: Decimal("24"),
    FrecuenciaPago.MENSUAL:   Decimal("12"),
}

def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), ROUND_HALF_UP)

def siguiente_fecha_vencimiento(actual: date, frecuencia: FrecuenciaPago) -> date:
    if frecuencia == FrecuenciaPago.SEMANAL:
        return actual + timedelta(weeks=1)
    elif frecuencia == FrecuenciaPago.QUINCENAL:
        return actual + timedelta(weeks=2)
    return actual + relativedelta(months=1)

def calcular_tasa_periodo(tasa: Decimal, frecuencia: FrecuenciaPago, es_anual: bool = True) -> Decimal:
    """
    Calcula la tasa del periodo. Si es_anual es True, divide por los periodos del año.
    De lo contrario, la trata como tasa del periodo directo. 
    En cualquier caso, la tasa pasada a la función YA DEBE SER UN DECIMAL (E.j. 0.20 para 20%).
    """
    # Fix crucial: Si el usuario introduce 20 (queriendo decir 20%), necesitamos garantizar que se trate como 0.20.
    # Si la tasa es > 1 (eje: 20), asumimos que el usuario puso porcentaje entero en UI y no decimal.
    if tasa > Decimal("1"):
        tasa = tasa / Decimal("100")
        
    if not es_anual:
        return tasa
    return tasa / PERIODOS_POR_ANO[frecuencia]

def calcular_cuota_fija(saldo: Decimal, tasa: Decimal, frecuencia: FrecuenciaPago, periodos_restantes: int, es_anual: bool = True) -> Decimal:
    r = calcular_tasa_periodo(tasa, frecuencia, es_anual)
    if r == 0:
        return redondear(saldo / periodos_restantes)
    factor = (1 + r) ** periodos_restantes
    cuota = saldo * (r * factor) / (factor - 1)
    return redondear(cuota)

def generar_tabla_amortizacion(capital: Decimal, tasa: Decimal, frecuencia: FrecuenciaPago, total_periodos: int, fecha_primer_pago: date, numero_inicio: int = 1, es_anual: bool = True) -> list[dict]:
    r = calcular_tasa_periodo(tasa, frecuencia, es_anual)
    cuota = calcular_cuota_fija(capital, tasa, frecuencia, total_periodos, es_anual)

    tabla = []
    saldo = capital
    fecha = fecha_primer_pago

    for i in range(total_periodos):
        numero_cuota = numero_inicio + i
        interes = redondear(saldo * r)
        capital_cuota = cuota - interes

        if i == total_periodos - 1:
            capital_cuota = saldo
            cuota_final = capital_cuota + interes
        else:
            cuota_final = cuota

        saldo = redondear(saldo - capital_cuota)

        tabla.append({
            "numero_cuota":    numero_cuota,
            "fecha_vencimiento": fecha,
            "capital_cuota":   redondear(capital_cuota),
            "interes_cuota":   interes,
            "total_cuota":     redondear(cuota_final),
            "saldo_restante":  max(saldo, Decimal("0")),
        })
        fecha = siguiente_fecha_vencimiento(fecha, frecuencia)

    return tabla

def generar_tabla_fija(capital: Decimal, tasa: Decimal, frecuencia: FrecuenciaPago, total_periodos: int, fecha_primer_pago: date, numero_inicio: int = 1, es_anual: bool = True) -> list[dict]:
    """
    Genera una tabla de amortización con Interés sobre Saldo (Decreciente).
    El interés se calcula sobre el capital pendiente en cada periodo.
    """
    r = calcular_tasa_periodo(tasa, frecuencia, es_anual)
    capital_por_periodo = redondear(capital / total_periodos)
    
    tabla = []
    saldo = capital
    fecha = fecha_primer_pago

    for i in range(total_periodos):
        numero_cuota = numero_inicio + i
        
        # Interés sobre el saldo actual
        interes_actual = redondear(saldo * r)
        
        if i == total_periodos - 1:
            capital_actual = saldo
        else:
            capital_actual = capital_por_periodo
            
        total_cuota = capital_actual + interes_actual
        saldo = redondear(saldo - capital_actual)

        tabla.append({
            "numero_cuota":    numero_cuota,
            "fecha_vencimiento": fecha,
            "capital_cuota":   redondear(capital_actual),
            "interes_cuota":   interes_actual,
            "total_cuota":     redondear(total_cuota),
            "saldo_restante":  max(saldo, Decimal("0")),
        })
        fecha = siguiente_fecha_vencimiento(fecha, frecuencia)

    return tabla

def aplicar_pago_logica(db: Session, prestamo: Prestamo, monto_recibido: Decimal, fecha_pago: date, metodo: MetodoPago, registrado_por_id: str, referencia: str = None, notas: str = None) -> dict:
    restante = monto_recibido
    resumen = {
        "aplicado_mora":    Decimal("0"),
        "aplicado_interes": Decimal("0"),
        "aplicado_capital": Decimal("0"),
        "cuotas_saldadas":  [],
        "recalculo":        False,
        "nueva_cuota":      None,
        "nuevo_saldo":      None,
    }

    cuotas_pendientes = (
        db.query(CuotaProgramada)
        .filter(
            CuotaProgramada.prestamo_id == prestamo.id,
            CuotaProgramada.estado.in_([EstadoCuota.PENDIENTE, EstadoCuota.PARCIAL, EstadoCuota.VENCIDA])
        )
        .order_by(CuotaProgramada.fecha_vencimiento)
        .all()
    )

    aplicaciones = []
    for cuota in cuotas_pendientes:
        if restante <= 0: break
        app = {"cuota": cuota, "mora_aplicada": Decimal("0"), "interes_aplicado": Decimal("0"), "capital_aplicado": Decimal("0")}
        
        # 1. Interés (Prioridad Maestro)
        interes_pendiente = cuota.interes_cuota - cuota.interes_pagado
        if interes_pendiente > 0 and restante > 0:
            pago_interes = min(restante, interes_pendiente)
            cuota.interes_pagado += pago_interes
            restante -= pago_interes
            resumen["aplicado_interes"] += pago_interes
            app["interes_aplicado"] += pago_interes

        # 2. Mora (Penalidad)
        mora_pendiente = cuota.monto_mora - cuota.mora_pagada
        if mora_pendiente > 0 and restante > 0:
            pago_mora = min(restante, mora_pendiente)
            cuota.mora_pagada += pago_mora
            restante -= pago_mora
            resumen["aplicado_mora"] += pago_mora
            app["mora_aplicada"] += pago_mora

        # 3. Capital (Principal)
        capital_pendiente = cuota.capital_cuota - cuota.capital_pagado
        if capital_pendiente > 0 and restante > 0:
            pago_capital = min(restante, capital_pendiente)
            cuota.capital_pagado += pago_capital
            restante -= pago_capital
            resumen["aplicado_capital"] += pago_capital
            app["capital_aplicado"] += pago_capital

        cuota.total_pagado = cuota.capital_pagado + cuota.interes_pagado + cuota.mora_pagada
        total_debido = cuota.total_cuota + cuota.monto_mora

        # --- TRASPASO DE CAPITAL FALTANTE ---
        # Si el usuario pagó al menos todo el interés y la mora, pero faltó capital
        if cuota.interes_pagado >= cuota.interes_cuota and cuota.mora_pagada >= cuota.monto_mora:
            capital_faltante = cuota.capital_cuota - cuota.capital_pagado
            if capital_faltante > 0 and restante <= 0:
                # Buscar la próxima cuota para sumarle el resto
                proxima_cuota = db.query(CuotaProgramada).filter(
                    CuotaProgramada.prestamo_id == prestamo.id,
                    CuotaProgramada.numero_cuota == cuota.numero_cuota + 1
                ).first()
                
                if proxima_cuota:
                    proxima_cuota.capital_cuota += capital_faltante
                    proxima_cuota.total_cuota += capital_faltante
                    
                    # Ajustar la cuota actual para que se marque como PAGADA
                    cuota.capital_cuota = cuota.capital_pagado
                    cuota.total_cuota = cuota.capital_cuota + cuota.interes_cuota
                    total_debido = cuota.total_cuota + cuota.monto_mora
        # ------------------------------------

        if cuota.total_pagado >= total_debido:
            cuota.estado = EstadoCuota.PAGADA
            cuota.fecha_pago = fecha_pago
            resumen["cuotas_saldadas"].append(cuota.numero_cuota)
        elif cuota.total_pagado > 0:
            cuota.estado = EstadoCuota.PARCIAL

        if any([app["mora_aplicada"], app["interes_aplicado"], app["capital_aplicado"]]):
            aplicaciones.append(app)

    if restante > 0:
        # Abono extraordinario (todo lo sobrante va a capital)
        resumen["aplicado_capital"] += restante
        resumen["recalculo"] = True
        restante = Decimal("0")

    pago = Pago(
        prestamo_id=prestamo.id, registrado_por=registrado_por_id,
        fecha_pago=fecha_pago, monto_recibido=monto_recibido,
        metodo_pago=metodo, numero_referencia=referencia, notas=notas,
        aplicado_mora=resumen["aplicado_mora"], aplicado_interes=resumen["aplicado_interes"],
        aplicado_capital=resumen["aplicado_capital"], genero_recalculo=resumen["recalculo"]
    )
    db.add(pago)
    db.flush()

    for app in aplicaciones:
        db.add(AplicacionPago(
            pago_id=pago.id, cuota_id=app["cuota"].id,
            monto_aplicado=app["mora_aplicada"] + app["interes_aplicado"] + app["capital_aplicado"],
            capital_aplicado=app["capital_aplicado"], interes_aplicado=app["interes_aplicado"],
            mora_aplicada=app["mora_aplicada"]
        ))

    # Actualización Maestro del Préstamo (Saldos Globales)
    prestamo.saldo_capital  = redondear(prestamo.saldo_capital - resumen["aplicado_capital"])
    prestamo.saldo_interes  = redondear(prestamo.saldo_interes - resumen["aplicado_interes"])
    prestamo.saldo_mora     = redondear(prestamo.saldo_mora - resumen["aplicado_mora"])
    
    if prestamo.saldo_capital <= 0: 
        prestamo.estado = EstadoPrestamo.COMPLETADO

    return resumen

def reajustar_tasa_prestamo(db: Session, prestamo: Prestamo, nueva_tasa_anual: Decimal, modo: str = "FUTURE_ONLY") -> bool:
    """
    Ajusta la tasa de interés de un préstamo y recalcula las cuotas.
    - FUTURE_ONLY: Solo cambia el interés de las cuotas pendientes/parciales.
    - ALL_PERIODS: Recalcula todo el préstamo desde cero.
    """
    from models.enums import EstadoCuota
    
    tasa_anual_decimal = nueva_tasa_anual / Decimal("100")
    prestamo.tasa_interes_anual = tasa_anual_decimal
    
    r = calcular_tasa_periodo(tasa_anual_decimal, prestamo.frecuencia, es_anual=True)
    
    for cuota in prestamo.tabla_pagos:
        # Modo ALL_PERIODS aplica a todas. modo FUTURE_ONLY solo a las no pagadas.
        if modo == "ALL_PERIODS" or cuota.estado != EstadoCuota.PAGADA:
            # El interés se calcula sobre el capital pendiente antes de esta cuota
            # En nuestra tabla: saldo_restante de la cuota anterior.
            if cuota.numero_cuota == 1:
                saldo_base = prestamo.monto_capital
            else:
                saldo_base = prestamo.tabla_pagos[cuota.numero_cuota-2].saldo_restante
            
            cuota.interes_cuota = redondear(saldo_base * r)
            cuota.total_cuota = cuota.capital_cuota + cuota.interes_cuota
    
    # Recalcular totales del préstamo
    prestamo.total_interes = sum(c.interes_cuota for c in prestamo.tabla_pagos)
    prestamo.total_a_pagar = prestamo.monto_capital + prestamo.total_interes
    
    # Actualizar saldo de intereses maestros
    prestamo.saldo_interes = sum(c.interes_cuota - c.interes_pagado for c in prestamo.tabla_pagos)
    
    return True

def get_user_dashboard_stats(db: Session, user_id: str, hoy: date):
    """
    Obtiene estadísticas detalladas para el dashboard del Oficial.
    """
    from sqlalchemy import func
    
    # Metas de cobro (Semana actual)
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    
    cuotas_semana = (
        db.query(CuotaProgramada)
        .join(Prestamo)
        .filter(
            Prestamo.creado_por_usuario_id == user_id,
            CuotaProgramada.fecha_vencimiento >= inicio_semana,
            CuotaProgramada.fecha_vencimiento <= fin_semana
        ).all()
    )
    
    total_proyectado_semana = sum((c.total_cuota + c.monto_mora) for c in cuotas_semana)
    total_cobrado_semana = sum((c.capital_pagado + c.interes_pagado + c.mora_pagada) for c in cuotas_semana)
    
    # Agenda de hoy
    agenda_hoy = (
        db.query(CuotaProgramada)
        .join(Prestamo)
        .filter(
            Prestamo.creado_por_usuario_id == user_id,
            CuotaProgramada.fecha_vencimiento == hoy,
            CuotaProgramada.estado != EstadoCuota.PAGADA
        ).all()
    )
    
    # Radar de Riesgo (1-3 días de atraso)
    ayer = hoy - timedelta(days=1)
    hace_3_dias = hoy - timedelta(days=3)
    riesgo_proximo = (
        db.query(CuotaProgramada)
        .join(Prestamo)
        .filter(
            Prestamo.creado_por_usuario_id == user_id,
            CuotaProgramada.fecha_vencimiento >= hace_3_dias,
            CuotaProgramada.fecha_vencimiento <= ayer,
            CuotaProgramada.estado != EstadoCuota.PAGADA
        ).all()
    )
    
    return {
        "meta_semanal": {
            "proyectado": total_proyectado_semana,
            "cobrado": total_cobrado_semana,
            "porcentaje": (total_cobrado_semana / total_proyectado_semana * 100) if total_proyectado_semana > 0 else 0
        },
        "agenda_hoy": agenda_hoy,
        "riesgo_proximo": riesgo_proximo
    }

def get_collection_efficiency(db: Session, start_date: date, end_date: date, user_id: str = None) -> dict:
    """
    Calcula la eficiencia de cobro: (Total Cobrado / Total Proyectado) en un rango de fechas.
    """
    query = db.query(CuotaProgramada).join(Prestamo).filter(
        CuotaProgramada.fecha_vencimiento >= start_date,
        CuotaProgramada.fecha_vencimiento <= end_date
    )
    
    if user_id:
        query = query.filter(Prestamo.creado_por_usuario_id == user_id)
        
    cuotas = query.all()
    
    proyectado = sum((c.total_cuota + c.monto_mora) for c in cuotas)
    cobrado = sum((c.capital_pagado + c.interes_pagado + c.mora_pagada) for c in cuotas)
    
    return {
        "proyectado": proyectado,
        "cobrado": cobrado,
        "eficiencia": (cobrado / proyectado * 100) if proyectado > 0 else 0
    }

def get_aging_portfolio(db: Session, user_id: str = None) -> dict:
    """
    Clasifica el saldo vencido por antigüedad (Aging Report).
    """
    from datetime import date
    hoy = date.today()
    
    query = db.query(CuotaProgramada).join(Prestamo).filter(
        CuotaProgramada.estado != EstadoCuota.PAGADA,
        CuotaProgramada.fecha_vencimiento < hoy
    )
    
    if user_id:
        query = query.filter(Prestamo.creado_por_usuario_id == user_id)
        
    cuotas = query.all()
    
    report = {
        "1-15": Decimal("0"),
        "16-30": Decimal("0"),
        "31-60": Decimal("0"),
        "60+": Decimal("0"),
        "total": Decimal("0")
    }
    
    for c in cuotas:
        dias = (hoy - c.fecha_vencimiento).days
        pendiente = (c.total_cuota + c.monto_mora) - (c.capital_pagado + c.interes_pagado + c.mora_pagada)
        
        if dias <= 15: report["1-15"] += pendiente
        elif dias <= 30: report["16-30"] += pendiente
        elif dias <= 60: report["31-60"] += pendiente
        else: report["60+"] += pendiente
        
        report["total"] += pendiente
        
    return report

def get_portfolio_profitability(db: Session, user_id: str = None) -> dict:
    """
    Calcula la rentabilidad real de la cartera basada en intereses y mora cobrados.
    """
    from sqlalchemy import func
    from models.pago import Pago
    query_pagos = db.query(
        func.sum(Pago.aplicado_interes).label("interes"),
        func.sum(Pago.aplicado_mora).label("mora"),
        func.sum(Pago.aplicado_capital).label("capital")
    ).join(Prestamo)
    
    if user_id:
        query_pagos = query_pagos.filter(Prestamo.creado_por_usuario_id == user_id)
        
    res = query_pagos.one()
    
    # Capital activo (lo que queda por cobrar)
    query_capital = db.query(func.sum(Prestamo.saldo_capital))
    if user_id:
        query_capital = query_capital.filter(Prestamo.creado_por_usuario_id == user_id)
    
    capital_activo = query_capital.scalar() or Decimal("0")
    
    return {
        "interes_cobrado": res.interes or Decimal("0"),
        "mora_cobrada": res.mora or Decimal("0"),
        "capital_recuperado": res.capital or Decimal("0"),
        "capital_activo": capital_activo,
        "total_utilidad": (res.interes or 0) + (res.mora or 0)
    }

def generar_recibo_pdf_bytes(pago: Pago) -> bytes:
    """
    Genera un recibo de pago profesional en formato PDF y devuelve los bytes.
    """
    from fpdf import FPDF
    import io
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Colores y fuentes
    pdf.set_fill_color(30, 41, 59) # Dark Slate
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    
    # Encabezado
    pdf.cell(0, 20, "COMPROBANTE DE PAGO - PRESTAPRO", ln=True, align="C", fill=True)
    pdf.ln(10)
    
    # Información General
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(95, 10, f"Recibo #: {str(pago.id)[:8].upper()}", border=0)
    pdf.cell(95, 10, f"Fecha: {pago.fecha_pago.strftime('%d/%m/%Y')}", border=0, ln=True, align="R")
    pdf.ln(5)
    
    # Datos del Cliente
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(0, 8, " DATOS DEL CLIENTE", ln=True, fill=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, f"Nombre: {pago.prestamo.cliente.nombre_completo}", ln=True)
    pdf.cell(0, 7, f"Prestamo #: {pago.prestamo.numero_prestamo}", ln=True)
    pdf.ln(5)
    
    # Detalle del Pago
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, " DETALLE DE LA TRANSACCION", ln=True, fill=True)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(140, 7, "Concepto", border="B")
    pdf.cell(50, 7, "Monto", border="B", ln=True, align="R")
    
    pdf.cell(140, 7, "Abono a Capital")
    pdf.cell(50, 7, f"${pago.aplicado_capital:,.2f}", ln=True, align="R")
    
    pdf.cell(140, 7, "Pago de Intereses")
    pdf.cell(50, 7, f"${pago.aplicado_interes:,.2f}", ln=True, align="R")
    
    if pago.aplicado_mora > 0:
        pdf.cell(140, 7, "Cargos por Mora")
        pdf.cell(50, 7, f"${pago.aplicado_mora:,.2f}", ln=True, align="R")
    
    pdf.ln(2)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(140, 10, "TOTAL RECIBIDO")
    pdf.cell(50, 10, f"${pago.monto_recibido:,.2f}", ln=True, align="R", border="T")
    
    pdf.ln(10)
    
    # Estado de Cuenta Actualizado
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, " ESTADO ACTUAL DE LA DEUDA", ln=True, fill=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    
    # Calculamos saldos pendientes
    saldo_capital = pago.prestamo.saldo_capital
    saldo_interes = pago.prestamo.saldo_interes
    saldo_mora = pago.prestamo.saldo_mora
    total_pendiente = saldo_capital + saldo_interes + saldo_mora
    
    pdf.cell(140, 7, "Saldo Capital Pendiente")
    pdf.cell(50, 7, f"${saldo_capital:,.2f}", ln=True, align="R")
    
    pdf.cell(140, 7, "Intereses Proyectados")
    pdf.cell(50, 7, f"${saldo_interes:,.2f}", ln=True, align="R")
    
    pdf.cell(140, 7, "Mora Acumulada")
    pdf.cell(50, 7, f"${saldo_mora:,.2f}", ln=True, align="R")
    
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(220, 38, 38) # Red
    pdf.cell(140, 10, "BALANCE TOTAL PENDIENTE")
    pdf.cell(50, 10, f"${total_pendiente:,.2f}", ln=True, align="R", border="T")
    
    pdf.ln(20)
    
    # Pie de página
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 5, "Este documento es un comprobante oficial de pago generado por PrestaPro.", ln=True, align="C")
    pdf.cell(0, 5, f"Metodo de Pago: {pago.metodo_pago.name} | Ref: {pago.numero_referencia or 'N/A'}", ln=True, align="C")
    pdf.cell(0, 5, "Gracias por su puntualidad.", ln=True, align="C")
    
    # Output a bytes
    return bytes(pdf.output())

def generar_resumen_pdf_bytes(prestamo: Prestamo) -> bytes:
    """
    Genera un reporte ejecutivo completo del estado de un préstamo.
    """
    from fpdf import FPDF
    import io
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Header
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 20, f"REPORTE EJECUTIVO - PRESTAMO {prestamo.numero_prestamo}", ln=True, align="C", fill=True)
    pdf.ln(10)
    
    # Cliente e Info General
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(0, 8, " INFORMACION DEL CLIENTE", ln=True, fill=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 7, f"Nombre: {prestamo.cliente.nombre_completo}")
    pdf.cell(95, 7, f"ID: {prestamo.cliente.numero_id}", ln=True, align="R")
    pdf.cell(95, 7, f"Telefono: {prestamo.cliente.telefono or 'N/A'}")
    pdf.cell(95, 7, f"Fecha Emision: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="R")
    pdf.ln(5)
    
    # Estado Financiero
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, " RESUMEN FINANCIERO", ln=True, fill=True)
    pdf.set_font("Arial", "", 10)
    
    col_w = 45
    pdf.cell(col_w, 7, "Capital Prestado", border="B")
    pdf.cell(col_w, 7, "Total Pagado", border="B")
    pdf.cell(col_w, 7, "Pendiente Total", border="B")
    pdf.cell(col_w, 7, "Progreso", border="B", ln=True)
    
    total_a_pagar = prestamo.total_a_pagar or Decimal("1")
    liquidado_pct = (prestamo.total_pagado / total_a_pagar) * 100
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(col_w, 10, f"${prestamo.monto_capital:,.2f}")
    pdf.cell(col_w, 10, f"${prestamo.total_pagado:,.2f}")
    pdf.cell(col_w, 10, f"${prestamo.monto_pendiente_total_dinamico:,.2f}")
    pdf.cell(col_w, 10, f"{liquidado_pct:,.0f}%", ln=True)
    pdf.ln(5)
    
    # Detalle de Saldos
    pdf.set_font("Arial", "B", 10)
    pdf.cell(60, 7, "Concepto")
    pdf.cell(40, 7, "Original", align="R")
    pdf.cell(40, 7, "Pagado", align="R")
    pdf.cell(40, 7, "Pendiente", align="R", ln=True)
    
    pdf.set_font("Arial", "", 10)
    # Capital
    pdf.cell(60, 7, "Capital Principal")
    pdf.cell(40, 7, f"${prestamo.monto_capital:,.2f}", align="R")
    pdf.cell(40, 7, f"${(prestamo.monto_capital - (prestamo.saldo_capital_dinamico or 0)):,.2f}", align="R")
    pdf.cell(40, 7, f"${(prestamo.saldo_capital_dinamico or 0):,.2f}", align="R", ln=True)
    
    # Interes
    pdf.cell(60, 7, "Intereses")
    pdf.cell(40, 7, f"${prestamo.total_interes:,.2f}", align="R")
    pdf.cell(40, 7, f"${(prestamo.total_interes - (prestamo.saldo_interes_dinamico or 0)):,.2f}", align="R")
    pdf.cell(40, 7, f"${(prestamo.saldo_interes_dinamico or 0):,.2f}", align="R", ln=True)

    # Mora (Si aplica)
    if (prestamo.saldo_mora_dinamico or 0) > 0 or prestamo.total_mora_generada > 0:
        pdf.cell(60, 7, "Cargos por Mora")
        pdf.cell(40, 7, f"${prestamo.total_mora_generada:,.2f}", align="R")
        pdf.cell(40, 7, f"${(prestamo.total_mora_generada - (prestamo.saldo_mora_dinamico or 0)):,.2f}", align="R")
        pdf.cell(40, 7, f"${(prestamo.saldo_mora_dinamico or 0):,.2f}", align="R", ln=True)

    pdf.ln(10)

    # Tabla de Pagos (Ultimos 10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, " HISTORIAL RECIENTE DE PAGOS", ln=True, fill=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 7, "Fecha", border="B")
    pdf.cell(60, 7, "Metodo", border="B")
    pdf.cell(50, 7, "Referencia", border="B")
    pdf.cell(50, 7, "Monto", border="B", ln=True, align="R")
    
    pdf.set_font("Arial", "", 10)
    ultimos_pagos = sorted(prestamo.pagos, key=lambda x: x.fecha_pago, reverse=True)[:10]
    for p in ultimos_pagos:
        pdf.cell(30, 7, p.fecha_pago.strftime('%d/%m/%Y'))
        pdf.cell(60, 7, p.metodo_pago.name)
        pdf.cell(50, 7, p.numero_referencia or "N/A")
        pdf.cell(50, 7, f"${p.monto_recibido:,.2f}", ln=True, align="R")
    
    if not ultimos_pagos:
        pdf.cell(0, 10, "No se registran pagos a la fecha.", ln=True, align="C")

    pdf.ln(20)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, "Este reporte es una proyeccion financiera basada en los datos actuales del sistema.", ln=True, align="C")
    pdf.cell(0, 5, "PrestaPro - Inteligencia Financiera", ln=True, align="C")

    return bytes(pdf.output())
