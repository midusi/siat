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
                TaskStatus(id="PROCESSING", name="Procesando"),
                TaskStatus(id="REVIEW", name="Revisión"),
                TaskStatus(id="APPROVED", name="Aprobada"),
            ])
            print("✔ TaskStatus cargado.")
        else:
            print("🔁 TaskStatus ya tiene datos.")

        session.commit()


def seed_provinces_districts_localities(csv_path="indec_datos.csv"):
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
    seed_provinces_districts_localities()
    print("✔ Datos cargados.")