import logging
from dataclasses import dataclass, field

from load.load_raw_jobs import load_raw_jobs, validated_job


logger = logging.getLogger(__name__)


@dataclass
class SourceBatch:
    jobs: list = field(default_factory=list)
    rejected: int = 0
    failed_pages: int = 0

    def add(self, job):
        try:
            self.jobs.append(validated_job(job))
        except (TypeError, ValueError) as error:
            self.reject(error)

    def reject(self, reason):
        self.rejected += 1
        logger.warning("Rejected source record: %s", reason)


def ingest_batch(source, batch):
    stats = {
        "attempted": len(batch.jobs) + batch.rejected,
        "accepted": len(batch.jobs),
        "rejected": batch.rejected,
        "failed_pages": batch.failed_pages,
    }
    if batch.rejected or batch.failed_pages:
        raise RuntimeError(f"{source} collection incomplete: {stats}")

    stats.update(load_raw_jobs(batch.jobs))
    logger.info("%s ingestion complete: %s", source, stats)
    return stats
