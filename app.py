from flask import Flask
from dotenv import load_dotenv
load_dotenv()  # Carga las variables de .env (ignorado si no existe en produccion)

from config import Config
from database import engine, Base
from routes.main import main_bp
from routes.auth import auth_bp
from routes.clientes import clientes_bp
from routes.prestamos import prestamos_bp
from flask import session, request
from datetime import timedelta

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    # Inicializar Base de Datos (si es necesario)
    # Base.metadata.create_all(bind=engine)

    # Registrar Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(clientes_bp)
    app.register_blueprint(prestamos_bp)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, port=Config.PORT)
