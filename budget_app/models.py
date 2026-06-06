from dataclasses import dataclass, field
from typing import List  # 리스트 형태의 타입 힌트를 사용하기 위해 불러옵니다.


@dataclass  # 이 장식자(Decorator)를 붙이면 파이썬이 자동으로 초기화(__init__) 코드를 만들어줍니다.
class Transaction:
    """거래 내역 한 건의 정보를 담는 클래스입니다."""

    id: str  # 거래의 고유 식별자입니다. (예: TX-123456)
    type: str  # 수입('income')인지 지출('expense')인지 구분합니다.
    date: str  # 거래 날짜를 YYYY-MM-DD 형식의 문자열로 저장합니다.
    amount: int  # 거래 금액을 양의 정수로 저장합니다.
    category: str  # 식비, 교통비 등의 카테고리 이름입니다.
    memo: str = ""  # 메모는 필수가 아니므로 기본값을 빈 문자열("")로 설정합니다.
    # 태그는 여러 개일 수 있으므로 리스트로 만들고, 기본값은 빈 리스트([])로 설정합니다.
    tags: List[str] = field(default_factory=list)


@dataclass
class Category:
    """카테고리 정보를 담는 클래스입니다."""

    name: str  # 카테고리의 이름입니다.


@dataclass
class Budget:
    """월별 예산 정보를 담는 클래스입니다."""

    month: str  # 예산이 적용될 월입니다. (예: 2024-01)
    amount: int  # 해당 월의 목표 예산 금액입니다.
