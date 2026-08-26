import hashlib
import json

def generate_hash(dataset_id: str, device_id: str, field_id: int) -> str:
    data = {"dataset_id": dataset_id, "device_id": device_id, "field_id": field_id}
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()