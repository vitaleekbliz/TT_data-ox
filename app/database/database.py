import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import  Numeric, DateTime, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import insert
import subprocess
import os

SCRIPT_PATH = "./dump_db.sh"
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Car(Base):
    __tablename__ = "cars"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    price_usd: Mapped[float] = mapped_column(Numeric(10, 2))
    odometer: Mapped[int]
    username: Mapped[str] = mapped_column(nullable=True)
    phone_number: Mapped[int] = mapped_column(BigInteger, nullable=True)
    image_url: Mapped[str] = mapped_column(nullable=True)
    images_count: Mapped[int] = mapped_column(default=0)
    car_number: Mapped[str] = mapped_column(nullable=True, index=True)
    car_vin: Mapped[str] = mapped_column(nullable=True, index=True)
    datetime_found: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def create_db_dump():
    status = ""
    """
    Triggers the bash script to create a compressed PostgreSQL dump.
    """
    
    # Check if script exists
    if not os.path.exists(SCRIPT_PATH):
        status = f"Error: {SCRIPT_PATH} not found."
        print(f"Error: {SCRIPT_PATH} not found.")
        return status

    try:
        # Run the bash script
        # Parameters: [script, container_name, user, db_name]
        process = subprocess.run(
            [SCRIPT_PATH, "db", "my_user", "app_db"],
            capture_output=True,
            text=True,
            check=True
        )
        
        output = process.stdout.strip()
        status = f"Database dump created successfully: {output}"
        print(f"Database dump created successfully: {output}")
        return output

    except subprocess.CalledProcessError as e:
        status = f"Backup failed! Error: {e.stderr}"
        print(f"Backup failed! Error: {e.stderr}")
        return status
    

async def get_db():
    async with async_session() as session:
        yield session

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    #print("PostgreSQL tables created successfully.")

# --- INSERT / UPSERT FUNCTION ---
async def upsert_cars(cars_list: list[Car]):
    await init_models()

    if not cars_list:
        return

    async with async_session() as session:
        async with session.begin():
            for car_obj in cars_list:
                car_obj.datetime_found = datetime.utcnow()

                car_data = {
                    k: v for k, v in car_obj.__dict__.items() 
                    if k != '_sa_instance_state'
                }

                stmt = insert(Car).values(car_data)

                # Decided to use link as dublicate checker instead of id, id scraping is turned off in car_card_parse
                # We map every field we want to refresh on a duplicate URL
                stmt = stmt.on_conflict_do_update(
                    index_elements=['url'],
                    set_={
                        "title": stmt.excluded.title,
                        "price_usd": stmt.excluded.price_usd,
                        "odometer": stmt.excluded.odometer,
                        "username": stmt.excluded.username,
                        "phone_number": stmt.excluded.phone_number,
                        "image_url": stmt.excluded.image_url,
                        "images_count": stmt.excluded.images_count,
                        "car_number": stmt.excluded.car_number,
                        "car_vin": stmt.excluded.car_vin,
                        # We use the current time to track the last time we saw this ad
                        "datetime_found": datetime.utcnow() 
                    }
                )
                await session.execute(stmt)
        # No need for explicit commit if using session.begin() context manager, 
        # but keeping it doesn't hurt.
        await session.commit()