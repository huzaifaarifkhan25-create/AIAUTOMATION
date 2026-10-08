from fastapi import APIRouter, Query, Request

from app.models.appointments import Appointment, AppointmentRequest

router = APIRouter(tags=["Appointment events"])


@router.post("/demo/reminder-workflow", status_code=201)
async def create_demo_workflow(request: Request):
    return await request.app.state.appointments.demo_workflow()


@router.post("/appointments", response_model=Appointment, status_code=202)
async def create_appointment(body: AppointmentRequest, request: Request):
    return await request.app.state.appointments.create(body)


@router.get("/appointments", response_model=list[Appointment])
async def list_appointments(request: Request, business_id: str | None = None,
                            limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    request.app.state.execution.require_supported()
    records = await request.app.state.store.list("appointments")
    if business_id:
        records = [record for record in records if record["business_id"] == business_id]
    records.sort(key=lambda record: (record["starts_at"], record["id"]))
    return records[offset:offset+limit]


@router.get("/appointments/{appointment_id}", response_model=Appointment)
async def get_appointment(appointment_id: str, request: Request):
    request.app.state.execution.require_supported()
    return await request.app.state.platform.require("appointments", appointment_id)


@router.post("/appointments/{appointment_id}/cancel", response_model=Appointment)
async def cancel_appointment(appointment_id: str, request: Request):
    return await request.app.state.appointments.cancel(appointment_id)
