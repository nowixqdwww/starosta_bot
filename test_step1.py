import hashlib, hmac, json, os, time
from urllib.parse import urlencode

os.environ["BOT_TOKEN"] = "123:TEST"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["BOT_USERNAME"] = "mybot"
if os.path.exists("test.db"):
    os.remove("test.db")

from fastapi.testclient import TestClient
from app.main import app

def init_data(user_id, name, token="123:TEST", age=0):
    fields = {"auth_date": str(int(time.time()) - age),
              "user": json.dumps({"id": user_id, "first_name": name})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)

def h(uid, name, **kw):
    return {"Authorization": "tma " + init_data(uid, name, **kw)}

c = TestClient(app)
assert c.get("/api/me").status_code == 401
assert c.get("/api/me", headers=h(1, "A", token="other")).status_code == 401
assert c.get("/api/me", headers=h(1, "A", age=90000)).status_code == 401
assert c.get("/api/me", headers=h(1, "A")).json()["registered"] is False

r = c.post("/api/register/leader", headers=h(1, "A"),
           json={"name": " Аня ", "group_name": "ИС-21", "institution": "МГТУ"})
assert r.status_code == 200, r.text
code = r.json()["group"]["invite_code"]
print("leader:", r.json())
assert c.post("/api/register/leader", headers=h(1, "A"),
              json={"name": "x", "group_name": "y", "institution": "z"}).status_code == 409

assert c.get("/api/invite/" + code.lower(), headers=h(2, "B")).json()["group_name"] == "ИС-21"
assert c.post("/api/register/student", headers=h(2, "B"),
              json={"name": "Боря", "invite_code": "WRONG"}).status_code == 404
r = c.post("/api/register/student", headers=h(2, "B"),
           json={"name": "Боря", "invite_code": code.lower()})
assert r.status_code == 200 and "invite_code" not in r.json()["group"]
print("student:", r.json())
print("OK")
