import re
from copy import deepcopy

# Simple PHI masking for logs: mask patient_id and any email/phone-like fields
def mask_phi(payload: dict) -> dict:
    data = deepcopy(payload)
    if "patient_id" in data:
        pid = data["patient_id"]
        data["patient_id"] = pid[:3] + "***" if isinstance(pid, str) and len(pid) > 3 else "***"
    # mask emails/phones crudely in string fields
    email_re = re.compile(r"[\w\.-]+@[\w\.-]+")
    phone_re = re.compile(r"\+?\d[\d\-\s]{6,}\d")

    def scrub(obj):
        if isinstance(obj, dict):
            return {k: scrub(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [scrub(x) for x in obj]
        if isinstance(obj, str):
            obj = email_re.sub("[email]", obj)
            obj = phone_re.sub("[phone]", obj)
            return obj
        return obj

    return scrub(data)
