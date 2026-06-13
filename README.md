# CLI 콘솔 가계부 애플리케이션

본 프로젝트는 Python 표준 라이브러리만을 사용하여 구현된 파일 기반 영구 저장 가계부입니다. 
제너레이터를 통한 대용량 파일 스트리밍 처리, 데코레이터 분리를 통한 공통 관심사 제어 등 구조적인 아키텍처 패턴이 적용되어 있습니다.



## 폴더 구조
```Plaintext
budget_app/
├── __main__.py         # 프로그램 진입점 (CLI 실행)
├── models.py           # 데이터 모델 정의 (dataclass)
├── repository.py       # 데이터 저장소 (파일 I/O, 제너레이터)
├── services.py         # 비즈니스 로직 및 데코레이터
└── cli.py              # 명령줄 인터페이스 파싱 및 대화형 입력 처리
README.md               # 프로젝트 설명서
```
## 1. 실행 방법
모듈 형식으로 실행합니다. (Python 3.8 이상 권장)
```bash
# 기본 사용법 및 도움말 확인
python -m budget_app --help

# 명령어별 상세 도움말
python -m budget_app list --help
```

## 2. 저장 파일 위치 및 형식
모든 데이터는 기본적으로 /data 폴더에 JSONL (JSON Lines) 형식으로 영구 저장됩니다.
각 줄이 독립적인 JSON 객체로 구성되어 파일 전체를 로드하지 않고 스트리밍 읽기에 유리합니다.

- transactions.jsonl: 거래 내역
- categories.jsonl: 카테고리 설정
- budgets.jsonl: 월별 예산

## 3. 주요 명령 예시
카테고리 추가 및 거래 내역 등록

```Bash
python -m budget_app category add  # (대화형) 'food' 등 입력
python -m budget_app add           # (대화형) 거래 내역 순차 입력
```

목록 및 검색 (스트리밍)

```Bash
python -m budget_app list --limit 5
python -m budget_app search --category food --type expense
```
월별 요약 및 예산

```Bash
python -m budget_app budget set --month 2024-01 --amount 500000
python -m budget_app summary --month 2024-01 --top 3
```
수정 및 삭제 (수정은 옵션 방식을 채택했습니다)

```Bash
python -m budget_app update --id TX-1234567890 --amount 20000 --memo "저녁식사"
python -m budget_app delete --id TX-1234567890
```


## 4. Import / Export CSV 스키마
데이터 마이그레이션을 위한 CSV 입출력 규격은 다음과 같습니다.
```bash
column, required,   설명
date,      Y,   YYYY-MM-DD 형식
type,      Y,   income 또는 expense
category,  Y,   사전에 등록되어 있는 카테고리명
amount,    Y,   양수 정수
memo,      N,   문자열
tags,      N,   "쉼표(,)로 구분된 태그 문자열"
```
- 내보내기: python -m budget_app export --out data.csv --month 2024-01

- 가져오기: python -m budget_app import --from data.csv

-----
## 5. 왜 main 파일명을 __main__.py로 구성하는가?

```python 
from .cli import run

if __name__ == "__main__":
    run()
```
- 현재 전체 코드는 budget_app 폴더 내에 위치하고 있음
    - __main__.py 구성하지 않으면 폴더 내에서 실행할 파일 명시 필요
    - ex. python main.py
- 폴더 내에 __main__.py 즉 진입점을 명시함으로서 모듈 실행 옵션 -m으로 폴더에서 바로 실행 가능
    - ex. python -m budget_app
- from .cli 처럼 상대경로 기반 import시 Import Error 발생
    - __main__.py를 진입점으로 구성해야 상대경로의 원래 위치 파악 가능
    - Import Error를 해결하는 방식

- if __name__ == "__main__":은 왜 쓰는가?
    - 직접 실행했을 때만 하위 명령어가 동작하게 하기 위함
    - 명시되지 않을 경우 타 파일에서 import만 한 경우에도 함수가 동작할 가능성 있음.
    - python main.py처럼 진입점으로 사용되어야만 하위 명령어가 동작할 수 있도록 함.

- calculator.py
```python
def add(a, b):
    return a + b
# 함수가 잘 동작하는지 테스트하기 위해 적어둔 코드
print("테스트 결과:", add(10, 20))
```
main.py
```python
import calculator # 계산기 모듈을 가져옵니다.
print("메인 프로그램을 시작합니다!")
```

## 6. 데코레이터 구성 방식
```python
def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 원래 실행하려던 함수를 실행합니다.
            return func(*args, **kwargs)
        except ValueError as e:
            # 입력값이 잘못되었을 때 발생하는 에러 처리
            print(f"[오류] {e}")
            print("[힌트] 입력하신 값의 형식이나 범위를 다시 확인해주세요.")
            sys.exit(1)  # 에러 상태 코드 1을 반환하며 종료합니다.
        except Exception as e:
            # 그 외 예상치 못한 모든 에러 처리
            print(f"[오류] 시스템 오류가 발생했습니다: {e}")
            sys.exit(1)

    return wrapper
```
- 매개변수로 기존 함수를 input -> wrapping된 새로운 함수를 return하는 방식
- @wraps 데코레이터 통해 wrapping되더라도 기존 함수명을 기억하도록 함.




## 7. yield와 return의 차이 