"""
test_bot.py - End-to-end integration tester for the candidate bot
"""

import sys
import json
import time
import urllib.request as request
import urllib.error as error

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8080"


def make_request(method, path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = request.Request(url, data=body, headers=headers, method=method)
    start = time.time()
    try:
        with request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            lat = (time.time() - start) * 1000
            return resp.status, json.loads(raw), lat
    except error.HTTPError as e:
        lat = (time.time() - start) * 1000
        raw = e.read().decode("utf-8")
        return e.code, json.loads(raw) if raw else {}, lat


def run_tests():
    print("==================================================")
    print("RUNNING VERA BOT END-TO-END TEST SUITE")
    print("==================================================")

    # 1. Test healthz
    status, data, lat = make_request("GET", "/v1/healthz")
    print(f"\n[1] GET /v1/healthz: HTTP {status} in {lat:.1f}ms")
    print(f"    Status: {data.get('status')}, Uptime: {data.get('uptime_seconds')}s, Contexts: {data.get('contexts_loaded')}")
    assert status == 200, f"Healthz failed: {status}"

    # 2. Test metadata
    status, data, lat = make_request("GET", "/v1/metadata")
    print(f"\n[2] GET /v1/metadata: HTTP {status} in {lat:.1f}ms")
    print(f"    Team: {data.get('team_name')}, Model: {data.get('model')}")
    assert status == 200, f"Metadata failed: {status}"

    # 3. Test context push (category)
    cat_dentists = json.load(open("dataset/categories/dentists.json", encoding="utf-8"))
    status, data, lat = make_request("POST", "/v1/context", {
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": cat_dentists,
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    print(f"\n[3] POST /v1/context (category): HTTP {status} in {lat:.1f}ms")
    print(f"    Accepted: {data.get('accepted')}, Ack: {data.get('ack_id')}")
    assert status == 200 and data.get("accepted"), "Category push failed"

    # Test idempotency (re-post version 1)
    status, data, _ = make_request("POST", "/v1/context", {
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": cat_dentists,
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    print(f"    Idempotency check (same version): HTTP {status}, Accepted: {data.get('accepted')}")
    assert status == 200 and data.get("accepted"), "Idempotency failed"

    # 4. Test context push (merchant)
    m_meera = json.load(open("expanded/merchants/m_001_drmeera_dentist_delhi.json", encoding="utf-8"))
    status, data, lat = make_request("POST", "/v1/context", {
        "scope": "merchant",
        "context_id": "m_001_drmeera_dentist_delhi",
        "version": 1,
        "payload": m_meera,
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    print(f"\n[4] POST /v1/context (merchant): HTTP {status} in {lat:.1f}ms")
    print(f"    Accepted: {data.get('accepted')}, Ack: {data.get('ack_id')}")
    assert status == 200 and data.get("accepted"), "Merchant push failed"

    # 5. Test context push (trigger)
    trg_jida = json.load(open("expanded/triggers/trg_023_competitor_opened_dentist.json", encoding="utf-8"))
    status, data, lat = make_request("POST", "/v1/context", {
        "scope": "trigger",
        "context_id": "trg_023_competitor_opened_dentist",
        "version": 1,
        "payload": trg_jida,
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    print(f"\n[5] POST /v1/context (trigger): HTTP {status} in {lat:.1f}ms")
    assert status == 200 and data.get("accepted"), "Trigger push failed"

    # 6. Test tick
    status, data, lat = make_request("POST", "/v1/tick", {
        "now": "2026-04-26T10:30:00Z",
        "available_triggers": ["trg_023_competitor_opened_dentist"]
    })
    print(f"\n[6] POST /v1/tick: HTTP {status} in {lat:.1f}ms")
    actions = data.get("actions", [])
    print(f"    Actions returned: {len(actions)}")
    for a in actions:
        print(f"    - Body: {a['body']}")
        print(f"      CTA: {a['cta']}, SendAs: {a['send_as']}, Rationale: {a['rationale']}")
    assert len(actions) == 1, "Tick failed to generate action"

    # 7. Test reply: Auto-Reply detection
    print("\n[7] Testing Multi-turn Scenarios:")
    conv_id = "test_conv_auto_1"
    auto_msg = "Thank you for contacting Dr. Meera's Clinic. Our team will respond shortly."
    status, data, lat = make_request("POST", "/v1/reply", {
        "conversation_id": conv_id,
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "customer_id": None,
        "from_role": "merchant",
        "message": auto_msg,
        "received_at": "2026-04-26T10:35:00Z",
        "turn_number": 2
    })
    print(f"    Turn 2 (1st auto-reply): action={data.get('action')}, body=\"{data.get('body')}\"")

    status, data, lat = make_request("POST", "/v1/reply", {
        "conversation_id": conv_id,
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "customer_id": None,
        "from_role": "merchant",
        "message": auto_msg,
        "received_at": "2026-04-26T10:36:00Z",
        "turn_number": 3
    })
    print(f"    Turn 3 (2nd repeated auto-reply): action={data.get('action')}, body=\"{data.get('body')}\"")
    assert data.get("action") == "end", "Auto-reply detector should return action: end on 2nd repeat"

    # 8. Test reply: Intent Transition
    conv_intent = "test_conv_intent_1"
    status, data, lat = make_request("POST", "/v1/reply", {
        "conversation_id": conv_intent,
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "customer_id": None,
        "from_role": "merchant",
        "message": "Ok lets do it. Go ahead and update the profile.",
        "received_at": "2026-04-26T10:40:00Z",
        "turn_number": 2
    })
    print(f"    Intent Transition: action={data.get('action')}, body=\"{data.get('body')}\"")
    assert data.get("action") == "send" and ("done" in data.get("body", "").lower() or "proceed" in data.get("body", "").lower()), "Intent transition should execute immediately"

    # 9. Test reply: Hostility / Stop
    conv_hostile = "test_conv_hostile_1"
    status, data, lat = make_request("POST", "/v1/reply", {
        "conversation_id": conv_hostile,
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "customer_id": None,
        "from_role": "merchant",
        "message": "Stop messaging me. This is spam.",
        "received_at": "2026-04-26T10:45:00Z",
        "turn_number": 2
    })
    print(f"    Hostility / Stop: action={data.get('action')}, body=\"{data.get('body')}\"")
    assert data.get("action") == "end", "Hostile message should trigger action: end"

    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
