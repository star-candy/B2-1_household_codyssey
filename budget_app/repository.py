import os  # 파일 및 폴더 생성, 존재 여부 확인을 위한 모듈입니다.
import json  # JSON 형식으로 데이터를 저장하고 읽기 위한 모듈입니다.
import tempfile  # 임시 파일을 안전하게 만들기 위한 모듈입니다.
import shutil  # 파일을 이동하거나 덮어쓰기 위한 모듈입니다.
from typing import Generator, List, Optional  # 타입 힌트를 위한 모듈입니다.
from .models import Transaction, Category, Budget


class FileRepository:
    """데이터를 파일에 저장하고 읽어오는 역할을 담당하는 클래스입니다."""

    def __init__(self, data_dir: str = "./data"):
        # 데이터를 저장할 폴더 경로를 설정합니다. 기본값은 './data' 입니다.
        self.data_dir = data_dir
        # 거래 내역, 카테고리, 예산을 저장할 각각의 파일 경로를 만듭니다.
        self.tx_file = os.path.join(data_dir, "transactions.jsonl")
        self.cat_file = os.path.join(data_dir, "categories.jsonl")
        self.budget_file = os.path.join(data_dir, "budgets.jsonl")

        # 프로그램 시작 시 파일들을 준비하는 함수를 호출합니다.
        self._init_files()

    def _init_files(self):
        """저장 폴더와 파일이 없으면 처음 만들어주는 함수입니다."""
        # 데이터 폴더가 존재하지 않으면
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)  # 폴더를 새로 만듭니다.
            print(f"[안내] 데이터 폴더를 생성했습니다: {self.data_dir}")

        # 거래 내역과 예산 파일이 없으면 빈 파일로 만들어둡니다.
        for filepath in [self.tx_file, self.budget_file]:
            if not os.path.exists(filepath):
                open(
                    filepath, "a"
                ).close()  # 'a'(추가) 모드로 열고 바로 닫으면 빈 파일이 생깁니다.

        # 카테고리 파일이 없거나, 파일 크기가 0(비어있음)이라면
        if not os.path.exists(self.cat_file) or os.path.getsize(self.cat_file) == 0:
            # 요구사항에 따라 기본 카테고리를 자동 생성합니다.
            default_categories = ["food", "transport", "rent", "salary", "etc"]
            for cat in default_categories:
                self.add_category(
                    Category(name=cat)
                )  # 기본 카테고리를 파일에 저장합니다.
            print("[안내] 기본 카테고리가 자동 생성되었습니다.")

    # ==========================================
    # 카테고리(Category) 관련 기능
    # ==========================================
    def get_categories(self) -> List[str]:
        """저장된 모든 카테고리 이름을 리스트로 반환합니다."""
        categories = []  # 카테고리 이름을 담을 빈 리스트를 만듭니다.
        # 파일을 읽기 모드('r')로 엽니다.
        with open(self.cat_file, "r", encoding="utf-8") as f:
            for line in f:  # 파일의 내용을 한 줄씩 읽습니다.
                if line.strip():  # 빈 줄이 아니라면
                    data = json.loads(line)  # JSON 문자열을 파이썬 딕셔너리로 바꿉니다.
                    categories.append(
                        data["name"]
                    )  # 리스트에 카테고리 이름을 추가합니다.
        return categories  # 완성된 리스트를 반환합니다.

    def add_category(self, category: Category):
        """새로운 카테고리를 파일 끝에 추가합니다."""
        # 파일을 추가 모드('a')로 엽니다.
        with open(self.cat_file, "a", encoding="utf-8") as f:
            # 딕셔너리를 JSON 문자열로 바꾸고, 줄바꿈(\n)을 더해 파일에 씁니다.
            f.write(json.dumps({"name": category.name}, ensure_ascii=False) + "\n")

    def remove_category(self, category_name: str):
        """특정 카테고리를 파일에서 삭제합니다. (임시 파일을 이용한 안전한 삭제)"""
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.data_dir
        )  # 임시 파일을 만듭니다.

        # 임시 파일을 쓰기 모드로, 원본 파일을 읽기 모드로 엽니다.
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            with open(self.cat_file, "r", encoding="utf-8") as original_file:
                for line in original_file:  # 원본 파일을 한 줄씩 읽습니다.
                    if not line.strip():
                        continue  # 빈 줄은 무시합니다.
                    data = json.loads(line)  # 파이썬 딕셔너리로 변환합니다.

                    # 삭제하려는 카테고리가 아니면 임시 파일에 다시 씁니다.
                    if data["name"] != category_name:
                        temp_file.write(line)

        # 모든 줄을 검사한 후, 임시 파일을 원본 파일 이름으로 덮어씁니다.
        shutil.move(temp_path, self.cat_file)

    # ==========================================
    # 예산(Budget) 관련 기능
    # ==========================================
    def set_budget(self, budget: Budget):
        """특정 월의 예산을 저장하거나 덮어씁니다."""
        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir)
        updated = False  # 이미 있는 월의 예산을 덮어썼는지 확인하는 변수입니다.

        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            with open(self.budget_file, "r", encoding="utf-8") as original_file:
                for line in original_file:
                    if not line.strip():
                        continue
                    data = json.loads(line)

                    # 입력받은 월과 파일에 적힌 월이 같다면 새로운 금액으로 덮어씁니다.
                    if data["month"] == budget.month:
                        new_data = {"month": budget.month, "amount": budget.amount}
                        temp_file.write(json.dumps(new_data) + "\n")
                        updated = True  # 덮어썼다고 표시합니다.
                    else:
                        temp_file.write(line)  # 다른 월의 예산은 그대로 유지합니다.

        shutil.move(temp_path, self.budget_file)  # 원본 교체

        # 만약 기존 파일에 해당 월의 예산이 없었다면, 파일 끝에 새로 추가합니다.
        if not updated:
            with open(self.budget_file, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps({"month": budget.month, "amount": budget.amount}) + "\n"
                )

    def get_budget(self, month: str) -> Optional[int]:
        """특정 월의 예산 금액을 가져옵니다. 없으면 None을 반환합니다."""
        with open(self.budget_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if data["month"] == month:  # 원하는 월을 찾으면
                        return data["amount"]  # 해당 금액을 반환합니다.
        return None  # 끝까지 찾았는데 없으면 None을 반환합니다.

    # ==========================================
    # 거래 내역(Transaction) 관련 기능
    # ==========================================
    def save_transaction(self, tx: Transaction):
        """새로운 거래 내역 한 줄을 파일 끝에 추가합니다."""
        with open(self.tx_file, "a", encoding="utf-8") as f:
            # tx.__dict__를 통해 클래스 데이터를 딕셔너리로 쉽게 변환할 수 있습니다.
            f.write(json.dumps(tx.__dict__, ensure_ascii=False) + "\n")

    def stream_transactions(self) -> Generator[Transaction, None, None]:
        """
        [핵심 요구사항: 제너레이터 기반 스트리밍 처리]
        파일에 데이터가 100만 줄이 있어도 한 번에 리스트로 만들지 않고,
        yield를 통해 한 줄씩 순차적으로 메모리에 올려서 반환합니다.
        """
        with open(self.tx_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    # 딕셔너리 데이터를 Transaction 객체로 만들어 반환합니다.
                    yield Transaction(**data)

    def delete_transaction(self, tx_id: str) -> bool:
        """아이디(ID)를 비교하여 거래 내역을 삭제합니다. 성공하면 True를 반환합니다."""
        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir)
        deleted = False  # 삭제 성공 여부를 기록합니다.

        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            with open(self.tx_file, "r", encoding="utf-8") as original_file:
                for line in original_file:
                    if not line.strip():
                        continue
                    data = json.loads(line)

                    if data["id"] == tx_id:
                        deleted = True  # 삭제 대상이면 파일에 쓰지 않고 무시합니다. (삭제 효과)
                    else:
                        temp_file.write(line)  # 삭제 대상이 아니면 그대로 씁니다.

        shutil.move(temp_path, self.tx_file)  # 작업 완료 후 원본을 교체합니다.
        return deleted

    def update_transaction(self, updated_tx: Transaction) -> bool:
        """아이디(ID)를 비교하여 기존 거래 내역을 새로운 내용으로 수정합니다."""
        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir)
        updated = False

        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            with open(self.tx_file, "r", encoding="utf-8") as original_file:
                for line in original_file:
                    if not line.strip():
                        continue
                    data = json.loads(line)

                    if data["id"] == updated_tx.id:
                        # 수정할 아이디를 찾으면, 기존 내용 대신 새 내용으로 덮어씁니다.
                        temp_file.write(
                            json.dumps(updated_tx.__dict__, ensure_ascii=False) + "\n"
                        )
                        updated = True
                    else:
                        temp_file.write(line)  # 대상이 아니면 그대로 둡니다.

        shutil.move(temp_path, self.tx_file)
        return updated
