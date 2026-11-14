import pickle
import sys
from pathlib import Path

from stackops.utils.installer_utils.installer_bulk_models import BulkInstallJob, BulkInstallOutcome
from stackops.utils.installer_utils.installer_class import Installer


def run_bulk_install_job(job_path: Path, outcome_path: Path) -> None:
    job = pickle.loads(job_path.read_bytes())
    if not isinstance(job, BulkInstallJob):
        raise TypeError(f"""Expected a BulkInstallJob in {job_path}, got {type(job).__name__}""")
    result = Installer(installer_data=job.installer_data).install_robust(install_request=job.install_request)
    outcome_path.write_bytes(pickle.dumps(BulkInstallOutcome(result=result)))


if __name__ == "__main__":
    run_bulk_install_job(job_path=Path(sys.argv[1]), outcome_path=Path(sys.argv[2]))
