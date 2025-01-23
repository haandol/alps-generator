# ALPS Generator

## 필수 요구사항
- Python 3.12+ 이상
- Amazon Bedrock 접근 권한

## 설치 방법

1. 저장소 클론

```bash
bash
git clone [repository-url]
cd alps-generator
```

2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate 
```

3. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
- 샘플 환경 변수 파일을 프로젝트 루트 디렉토리로 복사하여 설정하세요:
```bash
cp env/dev.env .env
```
- `.env` 파일을 열어 실제 값으로 수정하세요:
  - `AWS_DEFAULT_REGION`: AWS 리전 (예: us-east-1)
  - `BEDROCK_MODEL_ID`: 사용할 Bedrock 모델 ID

> ⚠️ 주의: `.env` 파일은 민감한 정보를 포함하고 있으므로 절대 Git에 커밋하지 마세요.

## 실행 방법

```bash
chainlit run alps_creator.py -w
```

이후 웹 브라우저에서 `http://localhost:8000`으로 접속하여 ALPS 생성기를 사용할 수 있습니다.