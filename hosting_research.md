# Opciones de Hosting Gratuito (2026)

Para validar el comportamiento del sistema en la nube sin incurrir en costos, estas son las mejores opciones actuales:

## 1. Aplicación (Flask / Python)

| Proveedor | Ventajas | Limitaciones |
| :--- | :--- | :--- |
| **Render** | Muy fácil de configurar. | La instancia se "duerme" tras 15 min de inactividad (cold start). |
| **Railway** | Excelente interfaz, despliegue rápido. | Funciona por créditos ($5 gratis al inicio), no es "gratis para siempre". |
| **PythonAnywhere** | Especializado en Python. | Solo permite una aplicación en el subdominio gratuito. |

## 2. Base de Datos (PostgreSQL)

| Proveedor | Capacidad | Nota |
| :--- | :--- | :--- |
| **Neon.tech** | 512 MB | **Recomendado.** Serverless, escala a cero, muy rápido. |
| **Supabase** | 500 MB | Es un PaaS completo (incluye Auth y Storage). |
| **Render DB** | Variable | Las bases de datos gratuitas en Render suelen expirar tras 90 días. |

## Recomendación de Despliegue para Prueba

1. **Backend**: [Render](https://render.com) (Web Service gratuito).
2. **Base de Datos**: [Neon](https://neon.tech) (PostgreSQL gratuito).
3. **Conexión**: Configurar la variable de entorno `SQLALCHEMY_DATABASE_URI` en Render apuntando a Neon.
