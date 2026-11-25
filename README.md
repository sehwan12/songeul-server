# 손글손글 · 평가 서버

손글손글 앱에서 보낸 글씨 이미지와 획 좌표를 받아 점수와 피드백을 돌려주는 FastAPI 서버입니다. 로그인과 학습 기록 조회를 처리하며, 자유 연습에 쓸 글자·단어·문장은 Gemini로 생성합니다.

앱 화면과 필기 입력 코드는 [Flutter 저장소](https://github.com/AI-WritingCorrection/writingCorrection_flutter)에 있습니다. 시연 영상과 APK도 그곳에서 볼 수 있습니다.

## 로컬에서 실행

Python 3.10과 Docker Compose가 필요합니다. 현재 [`docker-compose.yml`](docker-compose.yml)은 PostgreSQL만 실행합니다. FastAPI는 호스트에서 따로 실행합니다.

먼저 환경 파일을 만듭니다.

```sh
cp .env.example .env
```

`.env`의 PostgreSQL 설정은 아래 예시를 참고합니다. 포트 `5435`는 Compose가 호스트에 공개하는 포트입니다.

```dotenv
POSTGRES_USER=writing
POSTGRES_PASSWORD=local_dev_password
POSTGRES_DB=correction
DATABASE_URL=postgresql://writing:local_dev_password@localhost:5435/correction
STATIC_PROFILE_DIR=./static/profile
PUBLIC_BASE_URL=http://localhost:8000
```

- `JWT_SECRET_KEY`에는 개발용 키를 설정하고, `JWT_ALGORITHM`과 `JWT_ACCESS_EXPIRE_MINUTES`는 [`.env.example`](.env.example)을 참고합니다.
- Firebase 로그인을 사용하려면 Flutter 앱과 같은 Firebase 프로젝트의 서비스 계정 파일을 서버 루트에 `serviceAccountKey.json`으로 둡니다. 현 코드는 [`firebase.py`](firebase.py)에서 이 파일을 읽습니다.
- 연습 문장 생성을 사용하려면 `GEMINI_API_KEY`를 설정합니다.

```sh
docker compose up -d db
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p static/profile
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

실행 후 [Swagger UI](http://localhost:8000/docs)에서 요청과 응답 형식을 확인할 수 있습니다. 첫 평가 요청에서는 EasyOCR 가중치를 내려받느라 시간이 걸릴 수 있습니다.

## API

| 경로 | 역할 |
| --- | --- |
| `POST /api/step/evaluate` | 필기 이미지와 획 좌표 평가 |
| `POST /api/auth/login`, `POST /api/auth/signup` | Firebase 인증 결과를 바탕으로 로그인·가입 처리 |
| `GET /api/data/step`, `GET /api/data/practice` | 학습 단계와 연습 데이터 조회 |
| `GET /api/data/missionrecords/{user_id}`, `GET /api/user/stats/{user_id}` | 미션 기록과 점수 통계 조회 |
| `POST /api/text/generate` | 연습용 글자·단어·문장 생성 |

## 손글씨를 평가하는 방식

| 순서 | 보는 항목 | 확인하는 내용 |
| --- | --- | --- |
| 1 | 가독성 | EasyOCR로 읽은 글자를 목표 글자와 비교합니다. 글자가 다르면 후보와 초성·중성·종성의 일치 여부를 확인합니다. |
| 2 | 글자 전체 비율 | 획이 차지하는 영역을 필기 칸과 비교해 글자 크기와 가로·세로 비율을 확인합니다. |
| 3 | 획순과 방향 | 입력한 획의 순서와 시작·끝 좌표를 자모별 규칙과 비교합니다. |
| 4 | 자모 비율 | 글자 전체에서 각 자모가 차지하는 길이와 면적을 기준값과 비교합니다. |

## 코드 구조

| 경로 | 역할 |
| --- | --- |
| [`main.py`](main.py), [`controller/`](controller/) | FastAPI 앱과 API 라우터 |
| [`service/`](service/), [`aiModel/`](aiModel/) | 평가 로직과 OCR 모델 |
| [`domain/`](domain/), [`dto/`](dto/) | DB 모델과 API 요청·응답 형식 |
| [`alembic/`](alembic/) | PostgreSQL 스키마 변경 이력 |
| [`Dockerfile`](Dockerfile), [`nginx.conf`](nginx.conf) | 서버 이미지와 리버스 프록시 설정 |
| [`performance_tests/`](performance_tests/) | Locust 부하 테스트 시나리오 |

## 부하 테스트

[`locustfile.py`](performance_tests/locustfile.py)는 프로필·통계·학습 단계 조회, 문장 생성, 글씨 평가를 섞어 호출합니다. 시나리오가 `user_id=1`과 연습 글자가 나인 `step_id=1`을 사용하므로 해당 데이터가 있는 개발용 DB에서 실행합니다. 문장 생성 요청에는 Gemini 키가 필요합니다.

```sh
python -m pip install locust
locust -f performance_tests/locustfile.py --host http://localhost:8000
```

기존 부하 테스트 기록에서는 가상 사용자 32명 기준으로 약 13~15 RPS, 요청 실패 0건, 안정 구간의 p95 응답 시간 약 1~1.5초를 기록했습니다.
