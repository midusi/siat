import csv
import pandas as pd
from sqlmodel import Session, select
from models import (
    # VehicleType,
    # InferenceStatus,
    TaskStatus,
    Province,
    District,
    Locality,
)
from db import engine

# Added imports
from sqlalchemy.orm import Session as SASession
from models import User
from passlib.context import CryptContext


pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_static_data():
    with Session(engine) as session:
        # # VEHICLE TYPE
        # if not session.exec(select(VehicleType)).first():
        #     session.add_all([
        #         VehicleType(name="Auto"),
        #         VehicleType(name="Moto"),
        #         VehicleType(name="Camión"),
        #     ])
        #     print("✔ VehicleType cargado.")
        # else:
        #     print("🔁 VehicleType ya tiene datos.")

        # # INFERENCE STATUS
        # if not session.exec(select(InferenceStatus)).first():
        #     session.add_all([
        #         InferenceStatus(name="Procesando"),
        #         InferenceStatus(name="Pausado"),
        #         InferenceStatus(name="Finalizado"),
        #     ])
        #     print("✔ InferenceStatus cargado.")
        # else:
        #     print("🔁 InferenceStatus ya tiene datos.")

        # TASK STATUS
        if not session.exec(select(TaskStatus)).first():
            session.add_all([
                TaskStatus(id="VIDEO_UPLOADED", name="Video subido"),
                TaskStatus(id="CONFIGURED", name="Configurada"),
                TaskStatus(id="READY_TO_PROCESS", name="Lista para procesar"),
                TaskStatus(id="PROCESSING", name="Procesando"),
                TaskStatus(id="PROCESSED", name="Procesado"),
                TaskStatus(id="APPROVED", name="Aprobada"),
                TaskStatus(id="ARCHIVED", name="Archivada"),
            ])
            print("✔ TaskStatus cargado.")
        else:
            # Ensure ARCHIVED exists even if statuses were already seeded
            archived = session.exec(select(TaskStatus).where(TaskStatus.id == "ARCHIVED")).first()
            if not archived:
                session.add(TaskStatus(id="ARCHIVED", name="Archivada"))
                print("✔ TaskStatus ARCHIVED agregado.")
            else:
                print("🔁 TaskStatus ya tiene datos.")

        session.commit()


def seed_admin_user():
    # Use SQLAlchemy session directly bound to same engine URL
    from db import SessionLocal
    db: SASession = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                password=pwd.hash("admin"),  # cambiar en prod
                email="admin@example.com",
                first_name="Admin",
                last_name="User",
                role="ROLE_ADMIN",
                active=True,
            )
            db.add(admin)
            db.commit()
            print("✔ Usuario admin creado (username=admin, password=admin)")
        else:
            print("🔁 Usuario admin ya existe")
    finally:
        db.close()


def seed_provinces_districts_localities(csv_path="app/indec_datos.csv"):
    df = pd.read_csv(csv_path, sep=";")
    total_inserted = 0

    with Session(engine) as session:
        if not session.exec(select(Province)).first():
            for _, row in df.iterrows():
                locality_name = row["locality_name"].strip()
                district_name = row["district_name"].strip()
                province_name = row["province_name"].strip()

                # Insertar provincia si no existe
                province = session.exec(
                    select(Province).where(Province.name == province_name)
                ).first()
                if not province:
                    province = Province(name=province_name)
                    session.add(province)
                    session.commit()
                    session.refresh(province)

                # Insertar distrito si no existe
                district = session.exec(
                    select(District).where(
                        (District.name == district_name) &
                        (District.province_id == province.id)
                    )
                ).first()
                if not district:
                    district = District(name=district_name, province_id=province.id)
                    session.add(district)
                    session.commit()
                    session.refresh(district)

                # Insertar localidad si no existe
                locality = session.exec(
                    select(Locality).where(
                        (Locality.name == locality_name) &
                        (Locality.district_id == district.id)
                    )
                ).first()
                if not locality:
                    session.add(Locality(name=locality_name, district_id=district.id))
                    total_inserted += 1

            session.commit()
            print(f"✔ Se insertaron {total_inserted} localidades (y sus distritos/provincias si faltaban).")


if __name__ == "__main__":
    seed_static_data()
    seed_admin_user()
    seed_provinces_districts_localities()
    print("✔ Datos cargados.")