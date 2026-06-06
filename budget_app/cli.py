import argparse  # 터미널 명령어를 쉽게 처리하기 위한 파이썬 표준 라이브러리입니다.
from .repository import FileRepository
from .services import BudgetService


def create_parser():
    """사용자가 터미널에 입력할 명령어(add, list 등)와 옵션(--limit 등)의 규칙을 정의합니다."""
    parser = argparse.ArgumentParser(description="CLI 가계부 애플리케이션")

    # 여러 개의 서브 명령어(add, list, search 등)를 담을 그룹을 만듭니다.
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    # 1. add 명령어 규칙 생성
    subparsers.add_parser("add", help="대화형으로 새로운 거래 내역을 추가합니다.")

    # 2. list 명령어 규칙 생성
    list_parser = subparsers.add_parser("list", help="거래 내역을 목록으로 조회합니다.")
    list_parser.add_argument(
        "--limit", type=int, default=10, help="출력할 개수 (기본값: 10)"
    )

    # 3. search 명령어 규칙 생성
    search_parser = subparsers.add_parser(
        "search", help="조건에 맞는 거래 내역을 검색합니다."
    )
    search_parser.add_argument("--from", dest="date_from", help="시작일 (YYYY-MM-DD)")
    search_parser.add_argument("--to", dest="date_to", help="종료일 (YYYY-MM-DD)")
    search_parser.add_argument("--category", help="카테고리")
    search_parser.add_argument("--type", help="타입 (income/expense)")
    search_parser.add_argument("--q", dest="keyword", help="메모 포함 키워드")
    search_parser.add_argument("--tag", help="태그")

    # 4. summary 명령어 규칙 생성
    summary_parser = subparsers.add_parser("summary", help="월별 요약을 출력합니다.")
    summary_parser.add_argument("--month", required=True, help="조회할 월 (YYYY-MM)")
    summary_parser.add_argument(
        "--top", type=int, default=3, help="지출 TOP N (기본값: 3)"
    )

    # 5. budget 명령어 규칙 생성
    budget_parser = subparsers.add_parser("budget", help="월별 예산을 설정합니다.")
    budget_parser.add_argument("action", choices=["set"], help="수행할 동작")
    budget_parser.add_argument("--month", required=True, help="설정할 월 (YYYY-MM)")
    budget_parser.add_argument("--amount", type=int, required=True, help="예산 금액")

    # 6. category 명령어 규칙 생성
    category_parser = subparsers.add_parser("category", help="카테고리를 관리합니다.")
    category_parser.add_argument(
        "action", choices=["add", "list", "remove"], help="수행할 동작"
    )
    category_parser.add_argument("--name", help="카테고리 이름 (add/remove 시 필요)")

    # 7. update 명령어 규칙 생성
    update_parser = subparsers.add_parser(
        "update", help="대화형으로 거래 내역을 수정합니다."
    )
    update_parser.add_argument("--id", required=True, help="수정할 거래 ID")

    # 8. delete 명령어 규칙 생성
    delete_parser = subparsers.add_parser("delete", help="거래 내역을 삭제합니다.")
    delete_parser.add_argument("--id", required=True, help="삭제할 거래 ID")

    # 9. import 명령어 규칙 생성
    import_parser = subparsers.add_parser(
        "import", help="CSV 파일에서 거래 내역을 가져옵니다."
    )
    import_parser.add_argument(
        "--from", dest="in_file", required=True, help="불러올 CSV 파일 경로"
    )

    # 10. export 명령어 규칙 생성
    export_parser = subparsers.add_parser(
        "export", help="조건에 맞는 거래 내역을 CSV로 내보냅니다."
    )
    export_parser.add_argument("--out", required=True, help="저장할 CSV 파일 경로")
    export_parser.add_argument("--month", help="내보낼 월 (YYYY-MM)")
    export_parser.add_argument("--from", dest="date_from", help="시작일")
    export_parser.add_argument("--to", dest="date_to", help="종료일")

    return parser  # 완성된 파서 객체를 반환합니다.


def run():
    """CLI 애플리케이션의 메인 실행 흐름을 통제하는 함수입니다."""
    parser = create_parser()
    args = (
        parser.parse_args()
    )  # 사용자가 입력한 명령어와 옵션을 분석하여 args 객체에 담습니다.

    # 저장소와 서비스 객체를 생성합니다.
    repo = FileRepository()
    service = BudgetService(repo)

    # 명령어를 입력하지 않고 실행했다면 도움말을 보여주고 종료합니다.
    if not args.command:
        parser.print_help()
        return

    # 사용자가 입력한 명령어(args.command)에 따라 알맞은 서비스 로직을 실행합니다.
    if args.command == "add":
        print("--- 거래 추가 ---")
        # input() 함수를 이용해 대화형으로 한 줄씩 입력을 받습니다. (.strip()은 앞뒤 공백 제거)
        date = input("날짜(YYYY-MM-DD): ").strip()
        tx_type = input("타입(income/expense): ").strip()
        category = input("카테고리: ").strip()
        amount_str = input("금액(양수): ").strip()
        # 입력값이 숫자로만 이루어져 있으면 숫자로 변환하고, 아니면 에러를 유발하기 위해 -1을 넣습니다.
        amount = int(amount_str) if amount_str.isdigit() else -1
        memo = input("메모(선택): ").strip()

        tags_str = input("태그(쉼표로 구분, 없으면 엔터): ").strip()
        if tags_str:
            tags = [t.strip() for t in tags_str.split(",")]
        else:
            tags = []

        # 서비스에 데이터를 전달하여 저장하고, 발급된 아이디를 받아옵니다.
        tx_id = service.add_transaction(tx_type, date, amount, category, memo, tags)
        print(f"[저장 완료] id={tx_id}")

    elif args.command == "list":
        txs = service.list_transactions(args.limit)
        for tx in txs:
            print(
                f"{tx.id} | {tx.date} | {tx.type} | {tx.category} | {tx.amount} | {tx.memo}"
            )

    elif args.command == "search":
        txs = service.search_transactions(
            args.date_from,
            args.date_to,
            args.category,
            args.type,
            args.keyword,
            args.tag,
        )
        for tx in txs:
            print(
                f"{tx.id} | {tx.date} | {tx.type} | {tx.category} | {tx.amount} | {tx.memo}"
            )

    elif args.command == "summary":
        service.get_summary(args.month, args.top)

    elif args.command == "budget":
        service.set_budget(args.month, args.amount)

    elif args.command == "category":
        # hasattr/getattr 대신 옵션이 없을 때를 대비하여 기본값을 빈 문자열로 안전하게 전달합니다.
        name = args.name if args.name else ""
        service.manage_category(args.action, name)

    elif args.command == "update":
        service.update_transaction_interactive(args.id)

    elif args.command == "delete":
        service.delete_transaction(args.id)

    elif args.command == "export":
        service.export_csv(args.out, args.month, args.date_from, args.date_to)

    elif args.command == "import":
        service.import_csv(args.in_file)
