from uuid import uuid4

from app.errors import AppError
from app.models.workflow import Workflow, WorkflowNode, now


def generate_workflow(analysis):
    kind = analysis.automation_type
    if kind == "research_required":
        raise AppError(409, "insufficient_analysis", "Confirm an automation opportunity before generating a workflow")
    nodes = [
        WorkflowNode(id="event", type="webhook", parameters={"event": kind, "required_fields": ["contact_id", "contact_permission"]}),
        WorkflowNode(id="permission", type="condition", parameters={"field": "contact_permission", "equals": True, "on_false": "stop"}),
    ]
    if kind in {"appointment_reminders", "consultation_followup", "rebooking"}:
        nodes.append(WorkflowNode(id="wait", type="delay", parameters={"configure_timing": True, "cancel_if": "appointment_cancelled_or_contact_opted_out"}))
    if kind == "booking_assistant":
        nodes.append(WorkflowNode(id="calendar", type="calendar", parameters={"operation": "offer_available_consultation_slots", "requires_client_calendar": True}))
    nodes.extend([
        WorkflowNode(id="message", type="message", parameters={"channel": "configure_before_execution", "template": analysis.recommended_automation, "recheck_contact_permission": True}),
        WorkflowNode(id="record", type="database", parameters={"operation": "record_delivery_result", "requires_client_database": True}),
    ])
    return Workflow(
        id=str(uuid4()), business_id=analysis.business_id, analysis_id=analysis.id,
        name=analysis.recommended_automation, created_at=now(), nodes=nodes,
        connections=[(nodes[i].id, nodes[i+1].id) for i in range(len(nodes)-1)],
        required_configuration=["Execution engine (for example n8n)", "Client account credentials", "Client contact permission rules", "Message templates and channel", "Timing, cancellation, and retry rules"],
    )
