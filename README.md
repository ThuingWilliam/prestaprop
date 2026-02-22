# 💎 PrestaPro - Sistema Elite de Préstamos

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-black.svg?logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon.tech-336791.svg?logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952b3.svg?logo=bootstrap&logoColor=white)
![Status](https://img.shields.io/badge/Status-Activo-success.svg)

**PrestaPro** es una aplicación web moderna, intuitiva y completamente responsiva diseñada para la gestión profesional de créditos, préstamos y análisis financiero corporativo. Con un diseño "Glassmorphism" y modo oscuro elegante, ofrece una experiencia de usuario élite en cualquier dispositivo.

---

## 🚀 Características Principales

* **📊 Panel de Control Analítico:** Visualización en tiempo real de estadísticas clave y gráficas dinámicas (Chart.js).
* **📱 Diseño 100% Responsivo:** Interfaz adaptativa "Mobile-First" con menú inteligente Offcanvas nativo de Bootstrap 5.
* **👥 Gestión Integral de Clientes:** Perfiles detallados e historial crediticio por usuario.
* **💰 Operativa de Créditos:** Cotizador en vivo, amortización, cobros parciales y manejo de mora (aging y vencidos).
* **🛡️ Auditoría y Seguridad:** Registro detallado (bitácora) de todos los movimientos y control de accesos basado en roles (Administrador/Cobrador).
* **🏦 Tesorería y Caja:** Cuadre de caja diario, ingresos, egresos y comprobantes en PDF.

---

## 🛠️ Tecnologías Utilizadas

* **Backend:** Python, Flask, SQLAlchemy (ORM).
* **Base de Datos:** PostgreSQL en la nube (alojado en [Neon.tech](https://neon.tech)).
* **Frontend:** HTML5, CSS3 Avanzado (Glassmorphism), JavaScript (Vanilla), Bootstrap 5.3, FontAwesome 6.
* **Despliegue (Infraestructura):** Render (con `render.yaml` pre-configurado para modo gratuito).

---

## ⚙️ Instalación Local (Entorno de Desarrollo)

Sigue estos pasos para correr el proyecto en tu máquina local:

1. **Clonar el repositorio:**

    ```bash
    git clone https://github.com/ThuingWilliam/prestaprop.git
    cd prestaprop
    ```

2. **Crear y activar un entorno virtual:**

    ```bash
    python -m venv venv
    # En Windows:
    venv\Scripts\activate
    # En Mac/Linux:
    source venv/bin/activate
    ```

3. **Instalar dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configurar Variables de Entorno (.env):**
    Crea un archivo llamado `.env` en la raíz del proyecto y agrega tu conexión a la base de datos:

    ```env
    DATABASE_URL=postgresql://usuario:password@host/nombre_db
    SECRET_KEY=tu_super_clave_secreta_aqui
    FLASK_DEBUG=true
    PORT=5000
    ```

5. **Ejecutar la aplicación:**

    ```bash
    python app.py
    ```

    La aplicación estará disponible en `http://localhost:5000`.

---

## ☁️ Despliegue Directo a Render

El proyecto está preparado para hacer un despliegue sin contacto en [Render.com](https://render.com) utilizando *Blueprints*.

1. Crea una cuenta gratuita en Render.
2. Ve a **New +** > **Blueprint**.
3. Conecta este repositorio de GitHub.
4. Render leerá automáticamente el archivo `render.yaml` y configurará tu servicio web en la capa gratuita.
5. Te pedirá los valores para `DATABASE_URL` (tu string de Neon.tech) y `SECRET_KEY`.
6. ¡Guarda y el despliegue comenzará automáticamente!

---

¡Desarrollado con 💻 para optimizar el negocio crediticio!
