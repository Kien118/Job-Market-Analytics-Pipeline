from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    TIMESTAMP
)

from sqlalchemy.orm import declarative_base


Base = declarative_base()


class RawJob(Base):

    __tablename__ = "raw_jobs"

    job_id = Column(Integer, primary_key=True)

    source = Column(String(100))

    job_title = Column(Text)

    company_name = Column(Text)

    location = Column(Text)

    salary_text = Column(Text)

    description = Column(Text)

    posted_date = Column(Date)

    source_url = Column(Text)

    external_id = Column(Text)

    job_hash = Column(String(32), nullable=False, unique=True)

    ingested_at = Column(TIMESTAMP)
