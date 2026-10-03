from math import ceil


def page_response(*, items: list, total: int, limit: int, offset: int) -> dict:
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "page_size": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "total_pages": ceil(total / limit) if total else 0,
    }
