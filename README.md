# FitBook mini – CI/CD demo

Egyszerű edzőterem-órafoglaló REST API (FastAPI + SQLite), teljes CI/CD pipeline-nal GitHub Actions-ben.

Készítette: Juhász Jenő (LEG1AC) – DevOps kurzus projektfeladat

## Üzleti funkciók

| Végpont | Leírás |
| --- | --- |
| `GET /health` | Állapot és verzió |
| `GET /sessions` | Órák listája szabad helyekkel |
| `POST /sessions` | Óra létrehozása (csak `X-Role: admin` fejléccel) |
| `POST /sessions/{id}/bookings` | Foglalás; telt háznál várólista |
| `DELETE /bookings/{id}` | Lemondás; az első várólistás automatikusan bekerül |

Interaktív API-dokumentáció futás közben: `http://localhost:8000/docs`

## Pipeline (`.github/workflows/ci-cd.yml`)

Minden `main` ágra történő push után automatikusan:

1. **Build és teszt** – függőségek telepítése, 12 pytest teszt, legalább 80% lefedettség.
2. **Package** – Docker image build, feltöltés a GitHub Container Registrybe (`ghcr.io/<felhasználó>/fitbook-mini:<commit>`).
3. **Deploy** – a registryből letöltött image elindítása a sandbox környezetben, majd smoke teszt a futó alkalmazáson.

## Helyi futtatás

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -v                                   # tesztek
uvicorn app.main:app --port 8000            # alkalmazás
./scripts/smoke_test.sh http://localhost:8000
```

Dockerrel:

```bash
docker build -t fitbook-mini .
docker run -p 8000:8000 fitbook-mini
```
