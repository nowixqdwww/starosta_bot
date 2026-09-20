import hashlib, hmac, json, os, time
from urllib.parse import urlencode

os.environ["BOT_TOKEN"] = "123:TEST"
os.environ["DATABASE_URL"] = "sqlite:///./test_schedule.db"
if os.path.exists("test_schedule.db"):
    os.remove("test_schedule.db")

from fastapi.testclient import TestClient
from app.main import app


def h(uid, name="X"):
    fields = {"auth_date": str(int(time.time())), "user": json.dumps({"id": uid, "first_name": name})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", b"123:TEST", hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {"Authorization": "tma " + urlencode(fields)}


c = TestClient(app)
lead, stud, other = h(1), h(2), h(3)

# незарегистрированный не видит расписание
assert c.get("/api/schedule", headers=lead).status_code == 403

code = c.post("/api/register/leader", headers=lead,
              json={"name": "Аня", "group_name": "ИС-21", "institution": "МГТУ"}).json()["group"]["invite_code"]
c.post("/api/register/student", headers=stud, json={"name": "Боря", "invite_code": code})
c.post("/api/register/leader", headers=other,
       json={"name": "Витя", "group_name": "ПМ-11", "institution": "МГУ"})

# староста добавляет пары в неупорядоченном виде
a = c.post("/api/schedule", headers=lead, json={"weekday": 2, "title": " Физика ", "start_time": "11:10"})
assert a.status_code == 200 and a.json()["title"] == "Физика", a.text
c.post("/api/schedule", headers=lead, json={"weekday": 0, "title": "Математика", "start_time": "09:30"})
c.post("/api/schedule", headers=lead, json={"weekday": 0, "title": "Алгоритмы", "start_time": "08:00"})

lst = c.get("/api/schedule", headers=stud).json()
assert [(l["weekday"], l["start_time"]) for l in lst] == [(0, "08:00"), (0, "09:30"), (2, "11:10")], lst
print("sorted:", [l["title"] for l in lst])

# студент читать может, менять нет
assert c.post("/api/schedule", headers=stud, json={"weekday": 1, "title": "x", "start_time": "10:00"}).status_code == 403
lid = lst[0]["id"]
assert c.put(f"/api/schedule/{lid}", headers=stud, json={"weekday": 1, "title": "x", "start_time": "10:00"}).status_code == 403
assert c.delete(f"/api/schedule/{lid}", headers=stud).status_code == 403

# валидация
for bad in [{"weekday": 7, "title": "x", "start_time": "10:00"},
            {"weekday": 1, "title": "  ", "start_time": "10:00"},
            {"weekday": 1, "title": "x", "start_time": "25:00"},
            {"weekday": 1, "title": "x", "start_time": "9:30"}]:
    assert c.post("/api/schedule", headers=lead, json=bad).status_code == 422, bad

# чужая группа: не видит и не может менять
assert c.get("/api/schedule", headers=other).json() == []
assert c.put(f"/api/schedule/{lid}", headers=other, json={"weekday": 1, "title": "x", "start_time": "10:00"}).status_code == 404
assert c.delete(f"/api/schedule/{lid}", headers=other).status_code == 404

# правка и удаление
r = c.put(f"/api/schedule/{lid}", headers=lead, json={"weekday": 4, "title": "Алгоритмы (лаб)", "start_time": "13:00"})
assert r.json()["weekday"] == 4 and r.json()["title"] == "Алгоритмы (лаб)"
assert c.delete(f"/api/schedule/{lid}", headers=lead).json() == {"ok": True}
assert len(c.get("/api/schedule", headers=lead).json()) == 2
assert c.delete(f"/api/schedule/{lid}", headers=lead).status_code == 404
print("OK")
