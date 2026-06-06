import sys  # 프로그램 강제 종료(sys.exit)를 위해 사용합니다.
import csv  # CSV 파일 읽기/쓰기를 위해 사용합니다.
import uuid  # 고유한 무작위 ID를 생성하기 위해 사용합니다.
import os  # 파일 존재 여부 확인과 임시 파일 작업을 위해 사용합니다.
from functools import wraps  # 데코레이터 작성을 도와주는 모듈입니다.
from datetime import datetime  # 날짜 형식을 검사하기 위해 사용합니다.
from typing import List, Optional

from .models import Transaction, Category, Budget
from .repository import FileRepository


# ==========================================
# 공통 관심사 분리를 위한 데코레이터 (요구사항 필수)
# ==========================================
def handle_exceptions(func):
    """
    모든 서비스 함수에 이 데코레이터를 붙이면,
    에러가 났을 때 보기 싫은 '스택 트레이스(빨간색 긴 오류 메시지)' 대신
    깔끔한 원인과 힌트를 출력하고 프로그램을 종료(1)합니다.
    """

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


class BudgetService:
    """사용자의 요청을 받아 논리적인 처리를 수행하는 서비스 클래스입니다."""

    def __init__(self, repo: FileRepository):
        # 데이터 저장소 객체를 넘겨받아 사용합니다.
        self.repo = repo

    def _validate_date(self, date_str: str):
        """입력받은 문자열이 올바른 날짜 형식(YYYY-MM-DD)인지 검사합니다."""
        try:
            # 문자열을 날짜 객체로 변환 시도합니다. 실패하면 ValueError가 발생합니다.
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # 데코레이터에서 잡을 수 있도록 명확한 메시지와 함께 에러를 던집니다.
            raise ValueError(f"날짜 형식이 올바르지 않습니다 (YYYY-MM-DD): {date_str}")

    @handle_exceptions
    def add_transaction(
        self,
        tx_type: str,
        date: str,
        amount: int,
        category: str,
        memo: str,
        tags: List[str],
    ) -> str:
        """새로운 거래 내역을 검증하고 저장합니다."""
        self._validate_date(date)  # 날짜 형식 확인

        # 타입 검사
        if tx_type != "income" and tx_type != "expense":
            raise ValueError("타입은 'income' 또는 'expense'만 가능합니다.")

        # 금액 검사
        if amount <= 0:
            raise ValueError("금액은 0보다 큰 양수여야 합니다.")

        # 카테고리 검사: 저장소에 있는 목록에 포함되는지 확인합니다.
        registered_categories = self.repo.get_categories()
        if category not in registered_categories:
            raise ValueError(f"등록되지 않은 카테고리입니다: '{category}'")

        # TX-로 시작하는 6자리 무작위 문자열 고유 아이디를 생성합니다.
        tx_id = f"TX-{uuid.uuid4().hex[:6].upper()}"

        # 데이터 클래스 객체를 생성합니다.
        tx = Transaction(
            id=tx_id,
            type=tx_type,
            date=date,
            amount=amount,
            category=category,
            memo=memo,
            tags=tags,
        )

        # 저장소를 통해 파일에 저장합니다.
        self.repo.save_transaction(tx)
        return tx_id  # 생성된 아이디를 반환합니다.

    @handle_exceptions
    def list_transactions(self, limit: int) -> List[Transaction]:
        """스트리밍으로 데이터를 읽어와서 최신순으로 반환합니다."""
        transactions = []
        # 제너레이터(stream_transactions)를 통해 파일에서 한 줄씩 가져옵니다.
        for tx in self.repo.stream_transactions():
            transactions.append(tx)

        # 최신 데이터가 가장 아래에 저장되므로, 리스트 순서를 뒤집습니다.
        transactions.reverse()

        # 사용자가 요청한 개수(limit)만큼만 잘라서 반환합니다.
        return transactions[:limit]

    @handle_exceptions
    def search_transactions(
        self,
        date_from: str,
        date_to: str,
        category: str,
        tx_type: str,
        keyword: str,
        tag: str,
    ) -> List[Transaction]:
        """주어진 여러 조건에 맞는 거래 내역만 찾아냅니다."""
        results = []
        for tx in self.repo.stream_transactions():
            # 사용자가 해당 조건을 입력했는데, 데이터가 조건과 다르면 무시하고 넘어갑니다(continue).
            if date_from and tx.date < date_from:
                continue
            if date_to and tx.date > date_to:
                continue
            if category and tx.category != category:
                continue
            if tx_type and tx.type != tx_type:
                continue
            if keyword and keyword not in tx.memo:
                continue
            if tag and tag not in tx.tags:
                continue

            # 모든 관문을 통과했다면 결과 리스트에 추가합니다.
            results.append(tx)

        results.reverse()  # 최신순 정렬
        return results

    @handle_exceptions
    def get_summary(self, month: str, top_n: int):
        """특정 월의 수입, 지출, 잔액 및 카테고리별 지출을 계산합니다."""
        total_income = 0
        total_expense = 0
        category_expenses = {}  # 카테고리별 지출을 기록할 빈 딕셔너리입니다.
        has_data = False  # 데이터가 한 건이라도 있는지 확인하는 변수입니다.

        # 제너레이터를 통해 한 줄씩 확인합니다.
        for tx in self.repo.stream_transactions():
            # 해당 거래의 날짜가 사용자가 입력한 '월(예: 2024-01)'로 시작하는지 확인합니다.
            if tx.date.startswith(month):
                has_data = True  # 데이터를 찾았습니다.

                if tx.type == "income":
                    total_income += tx.amount  # 수입 누적
                elif tx.type == "expense":
                    total_expense += tx.amount  # 지출 누적

                    # 딕셔너리에 해당 카테고리가 없으면 0으로 초기화합니다.
                    if tx.category not in category_expenses:
                        category_expenses[tx.category] = 0
                    category_expenses[tx.category] += tx.amount  # 카테고리별 지출 누적

        # 만약 해당 월의 데이터가 전혀 없다면 안내를 출력하고 마칩니다.
        if not has_data:
            print(f"[안내] {month} 월의 데이터가 없습니다.")
            return

        balance = total_income - total_expense
        budget_amount = self.repo.get_budget(month)  # 설정된 예산이 있는지 확인합니다.

        # 기본 요약 정보 출력
        print(f"총 수입: {total_income}원")
        print(f"총 지출: {total_expense}원")
        print(f"잔액: {balance}원")

        # 예산이 설정되어 있다면 사용률을 계산하여 출력합니다.
        if budget_amount:
            usage_ratio = (total_expense / budget_amount) * 100
            print(f"예산: {budget_amount}원 (사용률 {usage_ratio:.1f}%)")
            if usage_ratio > 100:
                print("⚠️ [경고] 설정한 예산을 초과했습니다!")

        # 딕셔너리의 데이터를 지출 금액(x[1]) 기준으로 내림차순(reverse=True) 정렬합니다.
        print(f"\n지출 TOP {top_n}")
        sorted_categories = sorted(
            category_expenses.items(), key=lambda x: x[1], reverse=True
        )

        # 위에서부터 요청한 개수(top_n)만큼만 출력합니다. (enumerate는 1번부터 번호를 매깁니다)
        for i, (cat, amt) in enumerate(sorted_categories[:top_n], 1):
            print(f"{i}) {cat} {amt}원")

    @handle_exceptions
    def delete_transaction(self, tx_id: str):
        # 저장소의 삭제 기능이 True를 반환하면 성공, False를 반환하면 해당 아이디가 없는 것입니다.
        if self.repo.delete_transaction(tx_id):
            print(f"[삭제 완료] id={tx_id}")
        else:
            raise ValueError("해당 id를 가진 거래 내역이 존재하지 않습니다.")

    @handle_exceptions
    def update_transaction_interactive(self, tx_id: str):
        """특정 거래의 수정 모드로 진입하여, 변경할 내용만 입력받아 덮어씁니다."""
        target_tx = None
        # 수정할 데이터를 먼저 파일에서 찾아옵니다.
        for tx in self.repo.stream_transactions():
            if tx.id == tx_id:
                target_tx = tx
                break  # 찾았으면 더 이상 파일을 읽을 필요가 없으므로 반복문을 종료합니다.

        if not target_tx:
            raise ValueError("해당 id를 가진 거래 내역이 존재하지 않습니다.")

        print(f"[{tx_id} 수정 모드] 변경하지 않을 항목은 엔터를 누르세요.")

        # input()으로 입력을 받되, 엔터만 쳤다면(빈 문자열) 기존 값(target_tx)을 유지합니다.
        new_date = input(f"날짜 ({target_tx.date}): ").strip()
        if not new_date:
            new_date = target_tx.date
        self._validate_date(new_date)  # 날짜 형식 확인

        new_type = input(f"타입 ({target_tx.type}): ").strip()
        if not new_type:
            new_type = target_tx.type

        new_cat = input(f"카테고리 ({target_tx.category}): ").strip()
        if not new_cat:
            new_cat = target_tx.category
        if new_cat not in self.repo.get_categories():
            raise ValueError(f"등록되지 않은 카테고리입니다: {new_cat}")

        amt_input = input(f"금액 ({target_tx.amount}): ").strip()
        # 입력이 있으면 숫자로 변환하고, 없으면 기존 금액 유지
        new_amt = int(amt_input) if amt_input else target_tx.amount
        if new_amt <= 0:
            raise ValueError("금액은 양수여야 합니다.")

        new_memo = input(f"메모 ({target_tx.memo}): ").strip()
        if not new_memo:
            new_memo = target_tx.memo

        # 리스트 형태의 태그 문자열을 다시 리스트로 조립하는 과정입니다.
        current_tags_str = ",".join(target_tx.tags)
        tags_input = input(f"태그 (기존: {current_tags_str}): ").strip()
        if tags_input:
            new_tags = [t.strip() for t in tags_input.split(",")]
        else:
            new_tags = target_tx.tags

        # 수정된 내용으로 새 객체를 만듭니다.
        updated_tx = Transaction(
            id=tx_id,
            type=new_type,
            date=new_date,
            amount=new_amt,
            category=new_cat,
            memo=new_memo,
            tags=new_tags,
        )
        self.repo.update_transaction(updated_tx)  # 저장소에 덮어쓰기 요청
        print(f"[수정 완료] id={tx_id}")

    @handle_exceptions
    def manage_category(self, action: str, name: str = ""):
        """카테고리 목록 보기, 추가, 삭제 기능을 통합 관리합니다."""
        if action == "list":
            for cat in self.repo.get_categories():
                print(f"- {cat}")

        elif action == "add":
            if not name:
                raise ValueError("추가할 카테고리명을 입력하세요.")
            if name in self.repo.get_categories():
                raise ValueError("이미 존재하는 카테고리입니다.")
            self.repo.add_category(Category(name))
            print(f"[저장 완료] category={name}")

        elif action == "remove":
            if not name:
                raise ValueError("삭제할 카테고리명을 입력하세요.")

            # 카테고리 삭제 전, 해당 카테고리를 쓰는 거래가 있는지 확인합니다.
            is_used = False
            for tx in self.repo.stream_transactions():
                if tx.category == name:
                    is_used = True
                    break  # 하나라도 발견되면 멈춤

            if is_used:
                raise ValueError(
                    f"'{name}' 카테고리를 사용하는 거래 내역이 존재하여 삭제할 수 없습니다."
                )

            self.repo.remove_category(name)
            print(f"[삭제 완료] category={name}")

    @handle_exceptions
    def set_budget(self, month: str, amount: int):
        if amount <= 0:
            raise ValueError("예산은 양수여야 합니다.")
        self.repo.set_budget(Budget(month=month, amount=amount))
        print(f"[저장 완료] {month} 예산 {amount}원")

    @handle_exceptions
    def export_csv(self, out_file: str, month: str, date_from: str, date_to: str):
        """조건에 맞는 거래를 찾아 CSV 파일로 내보냅니다."""
        # 월 또는 날짜 기간 조건이 하나도 없으면 오류 처리
        if not month and not (date_from and date_to):
            raise ValueError("--month 또는 --from/--to 조건을 반드시 입력해야 합니다.")

        records_count = 0
        # CSV 파일을 쓰기 모드로 엽니다. newline='' 은 윈도우 환경에서 빈 줄이 생기는 것을 방지합니다.
        with open(out_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)  # CSV 작성기 객체 생성
            # 가장 윗줄에 헤더(컬럼명)를 작성합니다.
            writer.writerow(["date", "type", "category", "amount", "memo", "tags"])

            # 스트리밍으로 데이터를 한 줄씩 읽습니다.
            for tx in self.repo.stream_transactions():
                # 조건 검사: 조건에 맞지 않으면 건너뜁니다.
                if month and not tx.date.startswith(month):
                    continue
                if date_from and tx.date < date_from:
                    continue
                if date_to and tx.date > date_to:
                    continue

                # 리스트 형태의 태그를 '식비,점심' 처럼 콤마 문자열로 합칩니다.
                tags_str = ",".join(tx.tags)
                # 데이터 한 줄을 리스트로 묶어 CSV에 기록합니다.
                writer.writerow(
                    [tx.date, tx.type, tx.category, tx.amount, tx.memo, tags_str]
                )
                records_count += 1  # 기록한 건수를 하나 올립니다.

        print(f"[완료] {out_file} ({records_count} records)")

    @handle_exceptions
    def import_csv(self, in_file: str):
        """CSV 파일을 읽어와 거래 내역으로 일괄 등록합니다."""
        if not os.path.exists(in_file):
            raise ValueError(f"파일을 찾을 수 없습니다: {in_file}")

        imported_count = 0
        valid_categories = self.repo.get_categories()  # 유효한 카테고리 목록 준비

        # CSV 파일을 읽기 모드로 엽니다.
        with open(in_file, "r", encoding="utf-8") as f:
            # 첫 번째 줄(헤더)을 키(key)로 하는 딕셔너리 형태로 한 줄씩 읽어오는 리더기입니다.
            reader = csv.DictReader(f)
            for row in reader:
                # 카테고리가 등록된 목록에 없으면 저장하지 않고 건너뜁니다.
                if row["category"] not in valid_categories:
                    print(
                        f"⚠️ [건너뜀] 미등록 카테고리: {row['category']} (날짜: {row['date']})"
                    )
                    continue
                try:
                    # CSV의 빈 태그 문자열을 리스트로 변환하는 안전한 로직입니다.
                    tags_str = row.get("tags", "")
                    if tags_str:
                        # 콤마로 쪼갠 뒤 양쪽 공백을 제거한 리스트 생성
                        tags_list = [t.strip() for t in tags_str.split(",")]
                    else:
                        tags_list = []

                    # 기존 add_transaction 함수를 재사용하여 저장과 검증을 동시에 처리합니다.
                    self.add_transaction(
                        tx_type=row["type"],
                        date=row["date"],
                        amount=int(row["amount"]),  # 문자열 숫자를 정수(int)로 변환
                        category=row["category"],
                        memo=row.get("memo", ""),  # 메모가 비어있으면 빈 문자열 할당
                        tags=tags_list,
                    )
                    imported_count += 1
                except Exception as e:
                    # 중간에 데이터 형식이 이상한 줄이 있어도 프로그램이 뻗지 않고 다음 줄로 넘어갑니다.
                    print(f"⚠️ [건너뜀] 데이터 형식 오류 ({e}) - 내역: {row}")

        print(f"[완료] imported={imported_count}")
