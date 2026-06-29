from contextlib import asynccontextmanager
from typing import List
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, APIRouter
from pydantic_settings import BaseSettings
from sqlalchemy import String, Integer, Float, CheckConstraint, create_engine, select
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

     # Checks on the database level some conditions about price and stock
     __table_args__ = (
         CheckConstraint('precio >= 0.01', name='precio_minimo'),
         CheckConstraint('stock >= 0', name='stock_minimo'),
     )

     def __repr__(self) -> str:
         return (f"Almacen(id={self.id}, nombre={self.nombre}, descripcion={self.descripcion}, "
                 f"precio={self.precio}, stock={self.stock})")


# Entry DTO, request
class InfoProductRequest(BaseModel):
     nombre: str
     descripcion: str
     precio: Decimal = Field(ge=Decimal("0.01"), decimal_places=2)
     stock: int = Field(ge=0)

#DTO de salida, lo que devolvera la API
# En el DTO de salida no es necesario agregar las mismas validaciones que el de entrada?
class InfoProductDTO(BaseModel):
    id: int
    nombre: str
    descripcion: str
    precio: float
    stock: int

class ListaProductosResponse(BaseModel):
    products: List[InfoProductDTO]

def almacen_entity_to_dto(entity: Almacen) -> InfoProductDTO:
    return InfoProductDTO(
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

router = APIRouter(prefix="/almacen", tags=["almacen"])

# Operaciones CRUD
# GET /almacen/productos
# Obtiene todos los productos
@router.get("/productos", response_model=ListaProductosResponse)

def product_list(session: Session = Depends(get_db_session)) -> ListaProductosResponse:
    query = select(Almacen)
    almacen_db = session.scalars(query).all()
    dtos = [almacen_entity_to_dto(c) for c in almacen_db]
    return ListaProductosResponse(products=dtos)
# Check products by id
@router.get("/productos/{id}")

def get_product_id(id: int, session: Session = Depends(get_db_session)) -> InfoProductDTO:
    query = select(Almacen).where(Almacen.id == id)
    almacen_db = session.scalars(query).first()

    if almacen_db is None:
        raise HTTPException(status_code=404, detail="No se encuentra el producto")
    return almacen_entity_to_dto(almacen_db)

# Create products
@router.post("/productos")
def create_product(info: InfoProductRequest, session: Session = Depends(get_db_session)) -> InfoProductDTO:
    new_product = Almacen(
        nombre=info.nombre,
        descripcion=info.descripcion,
        precio=info.precio,
        stock=info.stock)
    session.add(new_product)
    session.commit()
    return almacen_entity_to_dto(new_product)

# Change product info
#
@router.put("/productos/{id}", response_model=InfoProductDTO)
def update_product(id:int, info: InfoProductRequest, session:  Session = Depends(get_db_session)):
    almacen_db = session.scalars(
        select(Almacen).where(Almacen.id == id)).one_or_none()
    if almacen_db is None:
        raise HTTPException(status_code=404, detail="No se encuentra el producto")
    almacen_db.nombre = info.nombre
    almacen_db.descripcion = info.descripcion
    almacen_db.precio = info.precio
    almacen_db.stock = info.stock
    session.add(almacen_db)
    session.commit()
    return almacen_entity_to_dto(almacen_db)

# Delete products by id
# Response model tells swagger how to document the response
@router.delete("/productos/{id}", response_model=InfoProductDTO)
def delete_product(id:int, session: Session = Depends(get_db_session)):
    almacen_db = (session.get(Almacen, id))
    if almacen_db is None:
        raise HTTPException(status_code=404, detail="No se encuentra el producto")
    dto = almacen_entity_to_dto(almacen_db)
    session.delete(almacen_db)
    session.commit()
    return dto
app.include_router(router)
if __name__ == "__main__":
    uvicorn.run("app:app", port=8080, reload=True)