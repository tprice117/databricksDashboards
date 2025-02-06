from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class CustomLimitOffsetPagination(LimitOffsetPagination):
    def get_paginated_response(self, data):
        offset_next = self.offset + self.limit
        if offset_next >= self.count:
            offset_next = self.count
        offset_previous = self.offset - self.limit
        if offset_previous >= offset_next:
            offset_previous = offset_next - self.limit
        if offset_previous < 0:
            offset_previous = 0
        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "limit": self.limit,
                "offset": self.offset,
                "offset_next": offset_next,
                "offset_previous": offset_previous,
                "count": self.count,
                "results": data,
            }
        )
