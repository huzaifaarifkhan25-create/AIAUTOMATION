import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.models.csv_import import CsvImportReport
from app.models.discovery import DiscoveryJob, DiscoveryRequest
from app.services.discovery import spreadsheet_csv
from collect_leads import collector_status

router = APIRouter(prefix="/discovery", tags=["Free browser pilot"])


@router.get("/collector-status")
async def status(request: Request):
    return await asyncio.to_thread(collector_status, request.app.state.settings.browser_runtime)


@router.post("/jobs", response_model=DiscoveryJob, status_code=202)
async def start(body: DiscoveryRequest, request: Request):
    return await request.app.state.discovery.start(body)


@router.get("/jobs", response_model=list[DiscoveryJob])
async def jobs(request: Request):
    return sorted(await request.app.state.store.list("discovery_jobs"),
                  key=lambda job: job["created_at"], reverse=True)[:100]


@router.get("/jobs/{job_id}", response_model=DiscoveryJob)
async def job(job_id: str, request: Request):
    return await request.app.state.discovery.require(job_id)


@router.post("/jobs/{job_id}/preview", response_model=CsvImportReport)
async def preview(job_id: str, request: Request):
    return await request.app.state.discovery.preview_or_import(job_id, True)


@router.post("/jobs/{job_id}/import", response_model=CsvImportReport)
async def commit(job_id: str, request: Request):
    return await request.app.state.discovery.preview_or_import(job_id, False)


@router.get("/jobs/{job_id}/csv")
async def download(job_id: str, request: Request):
    service = request.app.state.discovery
    job = await service.require(job_id)
    # Enforce success and original-file integrity through the same preview path.
    await service.preview_or_import(job_id, True)
    return Response(service.result(job), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="results.csv"'})


@router.get("/jobs/{job_id}/spreadsheet.csv")
async def download_spreadsheet(job_id: str, request: Request):
    service = request.app.state.discovery
    job = await service.require(job_id)
    await service.preview_or_import(job_id, True)
    return Response(spreadsheet_csv(service.result(job)), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="results-spreadsheet.csv"'})
