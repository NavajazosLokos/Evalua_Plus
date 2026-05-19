import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User
from schemas.usuario import UsuarioCreate, UsuarioResponse, Token

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# ── Configuración ─────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esta-clave-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def crear_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credenciales_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credenciales_error
    except JWTError:
        raise credenciales_error

    usuario = db.query(User).filter(User.email == email).first()
    if usuario is None:
        raise credenciales_error
    return usuario


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/registro", response_model=UsuarioResponse, status_code=201)
def registrar_usuario(datos: UsuarioCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario."""
    if db.query(User).filter(User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    nuevo = User(
        name=datos.name,
        email=datos.email,
        password_hash=hash_password(datos.password)
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Inicia sesión y devuelve un token JWT."""
    usuario = db.query(User).filter(User.email == form_data.username).first()
    if not usuario or not verificar_password(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

    token = crear_token({"sub": usuario.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UsuarioResponse)
def usuario_actual(usuario: User = Depends(get_usuario_actual)):
    """Devuelve los datos del usuario autenticado."""
    return usuario