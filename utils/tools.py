"""
여의도 맛집 검색기 AI Tools 정의
Claude AI가 사용할 수 있는 검색 도구들
"""

# AI가 사용할 수 있는 식당 검색 도구들
RESTAURANT_TOOLS = [
    {
        "name": "search_restaurants",
        "description": "여의도 지역 식당을 통합 검색합니다. 식당명, 카테고리, 메뉴명 등으로 검색 가능",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색어 (예: '중식당', '갈비찜', '매운 음식', '스타벅스')"
                },
                "limit": {
                    "type": "integer",
                    "description": "검색 결과 개수 (기본값: 10)",
                    "default": 10
                },
                "include_details": {
                    "type": "boolean",
                    "description": "메뉴 등 상세 정보 포함 여부 (기본값: false)",
                    "default": True
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_by_category",
        "description": "특정 카테고리의 식당들을 검색합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "식당 카테고리 (예: '중식당', '일식당', '한식', '카페')"
                },
                "limit": {
                    "type": "integer",
                    "description": "검색 결과 개수 (기본값: 10)",
                    "default": 10
                }
            },
            "required": ["category"]
        }
    },
    {
        "name": "search_by_menu",
        "description": "특정 메뉴를 제공하는 식당들을 검색합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "menu_keyword": {
                    "type": "string",
                    "description": "메뉴 키워드 (예: '갈비찜', '짬뽕', '파스타', '스시')"
                },
                "limit": {
                    "type": "integer",
                    "description": "검색 결과 개수 (기본값: 10)",
                    "default": 10
                }
            },
            "required": ["menu_keyword"]
        }
    },
    {
        "name": "search_by_price_range",
        "description": "특정 가격대의 메뉴를 제공하는 식당들을 검색합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_price": {
                    "type": "integer",
                    "description": "최소 가격 (원 단위)"
                },
                "max_price": {
                    "type": "integer",
                    "description": "최대 가격 (원 단위)"
                },
                "limit": {
                    "type": "integer",
                    "description": "검색 결과 개수 (기본값: 10)",
                    "default": 10
                }
            }
        }
    },
    {
        "name": "get_restaurant_details",
        "description": "특정 식당의 상세 정보를 조회합니다 (전체 메뉴, 가격 등)",
        "input_schema": {
            "type": "object",
            "properties": {
                "restaurant_name": {
                    "type": "string",
                    "description": "조회할 식당명"
                }
            },
            "required": ["restaurant_name"]
        }
    },
    {
        "name": "get_statistics",
        "description": "전체 식당 통계 정보를 조회합니다 (식당 수, 카테고리별 분포 등)",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "recommend_similar_restaurants",
        "description": "특정 식당과 유사한 다른 식당들을 추천합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "restaurant_name": {
                    "type": "string",
                    "description": "기준이 될 식당명"
                },
                "limit": {
                    "type": "integer",
                    "description": "추천 식당 수 (기본값: 5)",
                    "default": 5
                }
            },
            "required": ["restaurant_name"]
        }
    }
]


# 사용 예시와 가이드
TOOL_USAGE_EXAMPLES = {
    "search_restaurants": {
        "description": "가장 많이 사용되는 통합 검색",
        "examples": [
            {"query": "중식당", "limit": 5},
            {"query": "짬뽕", "include_details": True},
            {"query": "스타벅스"}
        ]
    },
    "search_by_category": {
        "description": "카테고리별 전문 검색",
        "examples": [
            {"category": "일식당"},
            {"category": "카페", "limit": 15}
        ]
    },
    "search_by_menu": {
        "description": "메뉴명으로 식당 찾기",
        "examples": [
            {"menu_keyword": "갈비찜"},
            {"menu_keyword": "파스타", "limit": 8}
        ]
    },
    "search_by_price_range": {
        "description": "가격대별 검색",
        "examples": [
            {"min_price": 10000, "max_price": 20000},
            {"max_price": 15000}
        ]
    },
    "get_restaurant_details": {
        "description": "특정 식당 상세 정보",
        "examples": [
            {"restaurant_name": "여의도 한정식"}
        ]
    },
    "get_statistics": {
        "description": "전체 통계 조회",
        "examples": [
            {}
        ]
    },
    "recommend_similar_restaurants": {
        "description": "유사 식당 추천",
        "examples": [
            {"restaurant_name": "스타벅스"},
            {"restaurant_name": "여의도 한정식", "limit": 3}
        ]
    }
}