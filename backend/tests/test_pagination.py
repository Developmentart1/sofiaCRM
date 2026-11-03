"""Tests para core.pagination — matan el mutante PageParams.offset off-by-one."""
from core.pagination import PageParams


def test_offset_zero_based():
    assert PageParams(page=1, page_size=20).offset == 0
    assert PageParams(page=2, page_size=20).offset == 20
    assert PageParams(page=3, page_size=10).offset == 20
