from contextlib import asynccontextmanager
from typing import List

import uvicorn
from fastapi import FastAPI
from pydantic_settings import BaseSettings
from sqlalchemy import String, Integer, Float, CheckConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from pydantic import BaseModel, Field
from decimal import Decimal



class BaseEntity(DeclarativeBase):
    pass

class Almacen(BaseEntity):
     __tablename__ = 'almacen'
     id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
     nombre: Mapped[str] = mapped_column(String(500))
     descripcion: Mapped[str] = mapped_column(String(2000))
     precio: Mapped[float] = mapped_column(Float())
     stock: Mapped[int] = mapped_column(Integer())

    # Chequeos a nivel base de datos de las condiciones de precio y stock
     __table_args__ = (
         CheckConstraint('precio >= 0.01', name='precio_minimo'),
         CheckConstraint('stock >= 0', name='stock_minimo'),
     )

     def __repr__(self) -> str:
         return (f"Almacen(id={self.id}, nombre={self.nombre}, descripcion={self.descripcion}, "
                 f"precio={self.precio}, stock={self.stock})")

# Dto de entrada (llega al request)
class InfoAlmacen(BaseModel):
     nombre: str
     descripcion: str
     precio: Decimal = Field(ge=Decimal("0.01"), decimal_places=2)
     stock: int = Field(ge=0)

#DTO de salida, lo que devolvera la API
# En el DTO de salida no es necesario agregar las mismas validaciones que el de entrada?
class InfoAlmacenDTO(BaseModel):
    id: int
    nombre: str
    descripcion: str
    precio: float
    stock: int

class ListaAlmacenResponse(BaseModel):
    almacenes: List[InfoAlmacenDTO]

def almacen_entity_to_dto(entity: Almacen) -> InfoAlmacenDTO:
    return InfoAlmacenDTO(
        id=entity.id,
        nombre=entity.nombre,
        descripcion=entity.descripcion,
        precio=entity.precio,
        stock=entity.stock)

class APPSettings(BaseSettings):
    database_url: str = "sqlite:///almacen.db"
    root_path: str = "/almacen"

db_engine = create_engine(APPSettings().database_url, echo=True)

def crea_db_tables():
    BaseEntity.metadata.create_all(db_engine)

def get_db_session():
    with Session(db_engine) as session:
        yield session

@asynccontextmanager
async def lifespan(_: FastAPI):
    crea_db_tables()
    yield
    pass

app = FastAPI(root_path=APPSettings().root_path, docs_url="/", lifespan=lifespan)
if __name__ == "__main__":
    uvicorn.run("app:app", port=8080, reload=True)