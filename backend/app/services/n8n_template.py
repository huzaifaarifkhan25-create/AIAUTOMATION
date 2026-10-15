"""Native n8n graph: prepare an acknowledgement, return a CRM task instruction.

The CRM commits the task only after reading back a successful n8n execution.
No delivery node, arbitrary URL or code node is present in this template.
"""
def inquiry_template(name, path, credential_id=None):
    credential = {"httpHeaderAuth": {"id": credential_id, "name": "AIAutomation inquiry authentication"}} if credential_id else {}
    fields = [("run_id", "={{ $json.body.run_id }}"),
              ("business_id", "={{ $json.body.business_id }}"),
              ("contact_reference", "={{ $json.body.contact_reference }}"),
              ("inquiry", "={{ $json.body.inquiry }}"),
              ("acknowledgement", "={{ $json.body.acknowledgement }}"),
              ("followup_at", "={{ $json.body.followup_at }}"),
              ("execution_id", "={{ $execution.id }}"),
              ("delivery_status", "unsent_draft")]
    return {"name": name[:128], "nodes": [
        {"id": "inquiry", "name": "Receive inquiry", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [0, 0], "webhookId": path,
         "parameters": {"httpMethod": "POST", "path": path, "authentication": "headerAuth", "responseMode": "responseNode", "options": {}},
         "credentials": credential},
        {"id": "prepare", "name": "Prepare follow-up", "type": "n8n-nodes-base.set", "typeVersion": 3.4,
         "position": [260, 0], "parameters": {"assignments": {"assignments": [
             {"id": key, "name": key, "value": value, "type": "string"} for key, value in fields]}, "options": {}}},
        {"id": "respond", "name": "Return task instruction", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.4,
         "position": [520, 0], "parameters": {"respondWith": "json", "responseBody": "={{ $json }}", "options": {}}}
    ], "connections": {
        "Receive inquiry": {"main": [[{"node": "Prepare follow-up", "type": "main", "index": 0}]]},
        "Prepare follow-up": {"main": [[{"node": "Return task instruction", "type": "main", "index": 0}]]}
    }, "settings": {"executionOrder": "v1", "saveDataSuccessExecution": "all", "saveDataErrorExecution": "all"}}
