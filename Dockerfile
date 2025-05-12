# NASOSv5_mod3 Bot Dockerfile
# 멀티스테이지 빌드를 사용하여 최종 이미지 크기 최소화

# 빌드 스테이지
FROM python:3.11-slim AS builder

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 종속성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    g++ \
    git \
    libssl-dev \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install --no-cache-dir poetry==1.5.1

# Poetry 구성: 가상 환경 생성하지 않음
RUN poetry config virtualenvs.create false

# 프로젝트 종속성 파일 복사
COPY pyproject.toml poetry.lock* ./

# 종속성 설치 (--no-root: 프로젝트 자체는 설치하지 않음)
RUN poetry install --no-interaction --no-ansi --no-root --only main

# TA-Lib 설치 (기술적 분석 라이브러리)
RUN curl -L -o /tmp/ta-lib-0.4.0-src.tar.gz http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf /tmp/ta-lib-0.4.0-src.tar.gz -C /tmp \
    && cd /tmp/ta-lib \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && rm -rf /tmp/ta-lib-0.4.0-src.tar.gz /tmp/ta-lib \
    && pip install --no-cache-dir ta-lib

# 실행 스테이지
FROM python:3.11-slim

# 보안: 루트가 아닌 사용자 생성
RUN groupadd -r nasos && useradd -r -g nasos nasos

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 종속성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 빌드 스테이지에서 설치된 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/lib/libta_lib* /usr/lib/

# 소스 코드 복사
COPY . .

# 로그 및 데이터 디렉토리 생성
RUN mkdir -p /app/logs /app/data \
    && chown -R nasos:nasos /app

# 보안: 루트가 아닌 사용자로 전환
USER nasos

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/nasos/.local/bin:$PATH"

# 헬스체크
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/api/v1/health')" || exit 1

# 기본 명령
CMD ["python", "-m", "src.main"]
