"""
AI용 식당 검색 함수들
Elasticsearch 기반 여의도 식당 검색 시스템
"""

import json
from typing import Dict, List, Any, Optional, Union
from elasticsearch import Elasticsearch
from datetime import datetime


class RestaurantSearchAI:
    """
    AI가 사용할 수 있는 식당 검색 클래스
    """
    
    def __init__(self, es_host: str = "localhost", es_port: int = 9200, index_name: str = "restaurants"):
        """
        Elasticsearch 연결 초기화
        
        Args:
            es_host: Elasticsearch 호스트
            es_port: Elasticsearch 포트
            index_name: 인덱스 이름
        """
        self.es_client = Elasticsearch([f"{es_host}:{es_port}"])
        self.index_name = index_name
    
    def search_restaurants(
        self, 
        query: str, 
        limit: int = 10,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        🔍 통합 식당 검색 (AI 메인 검색 함수)
        
        Args:
            query: 검색어 (예: "중식당", "갈비찜", "매운 음식")
            limit: 결과 개수 제한 (기본 10개)
            include_details: 상세 정보 포함 여부 (메뉴, 가격 등)
        
        Returns:
            {
                "total": 총 검색 결과 수,
                "results": [식당 정보 리스트],
                "query": 검색어,
                "search_time": 검색 시간
            }
        """
        try:
            start_time = datetime.now()
            
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            # 정확한 매칭 (최고 우선순위)
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["name^10", "category^8"],
                                    "type": "phrase",
                                    "boost": 3
                                }
                            },
                            # 식당명과 카테고리 일반 검색
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["name^5", "category^3", "name.ngram^2"],
                                    "type": "cross_fields",
                                    "boost": 2
                                }
                            },
                            # 메뉴명 검색 (nested)
                            {
                                "nested": {
                                    "path": "menu",
                                    "query": {
                                        "multi_match": {
                                            "query": query,
                                            "fields": ["menu.name^5", "menu.name.ngram^3", "menu.description^2"],
                                            "type": "cross_fields"
                                        }
                                    },
                                    "boost": 4
                                }
                            },
                            # 전체 텍스트 ngram 검색
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["full_text_search.ngram"],
                                    "type": "cross_fields"
                                }
                            },
                            # 부분 매칭 (wildcard)
                            {
                                "bool": {
                                    "should": [
                                        {"wildcard": {"name": f"*{query}*"}},
                                        {"wildcard": {"category": f"*{query}*"}},
                                        {
                                            "nested": {
                                                "path": "menu",
                                                "query": {
                                                    "bool": {
                                                        "should": [
                                                            {"wildcard": {"menu.name": f"*{query}*"}},
                                                            {"wildcard": {"menu.description": f"*{query}*"}}
                                                        ]
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "_source": ["name", "category", "menu", "restaurant_id"] if include_details else ["name", "category"],
                "size": limit
            }
            
            response = self.es_client.search(index=self.index_name, body=search_body)
            end_time = datetime.now()
            
            results = []
            for hit in response['hits']['hits']:
                restaurant = {
                    "name": hit['_source']['name'],
                    "category": hit['_source']['category'],
                    "score": round(hit['_score'], 2),
                    "id": hit['_source'].get('restaurant_id', hit['_id'])
                }
                
                if include_details and 'menu' in hit['_source']:
                    restaurant['menu'] = hit['_source']['menu']
                    restaurant['menu_count'] = len(hit['_source']['menu'])
                
                results.append(restaurant)
            
            return {
                "total": response['hits']['total']['value'],
                "results": results,
                "query": query,
                "search_time_ms": int((end_time - start_time).total_seconds() * 1000)
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "total": 0,
                "results": [],
                "query": query
            }
    
    def search_by_category(self, category: str, limit: int = 10) -> Dict[str, Any]:
        """
        🏷️ 카테고리별 식당 검색
        
        Args:
            category: 카테고리 (예: "중식당", "일식당", "카페")
            limit: 결과 개수
        
        Returns:
            카테고리에 해당하는 식당 목록
        """
        try:
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"category": category}},
                            {"wildcard": {"category": f"*{category}*"}}
                        ]
                    }
                },
                "_source": ["name", "category"],
                "size": limit
            }
            
            response = self.es_client.search(index=self.index_name, body=search_body)
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    "name": hit['_source']['name'],
                    "category": hit['_source']['category'],
                    "score": round(hit['_score'], 2)
                })
            
            return {
                "total": response['hits']['total']['value'],
                "results": results,
                "category": category
            }
            
        except Exception as e:
            return {"error": str(e), "total": 0, "results": []}
    
    def search_by_menu(self, menu_keyword: str, limit: int = 10) -> Dict[str, Any]:
        """
        🍽️ 메뉴명으로 식당 검색
        
        Args:
            menu_keyword: 메뉴 키워드 (예: "갈비찜", "짬뽕", "파스타")
            limit: 결과 개수
        
        Returns:
            해당 메뉴를 제공하는 식당 목록
        """
        try:
            search_body = {
                "query": {
                    "nested": {
                        "path": "menu",
                        "query": {
                            "bool": {
                                "should": [
                                    {
                                        "multi_match": {
                                            "query": menu_keyword,
                                            "fields": ["menu.name^3", "menu.description"],
                                            "type": "cross_fields"
                                        }
                                    },
                                    {
                                        "wildcard": {
                                            "menu.name": f"*{menu_keyword}*"
                                        }
                                    }
                                ]
                            }
                        },
                        "inner_hits": {
                            "size": 3,
                            "_source": ["menu.name", "menu.price"]
                        }
                    }
                },
                "_source": ["name", "category"],
                "size": limit
            }
            
            response = self.es_client.search(index=self.index_name, body=search_body)
            
            results = []
            for hit in response['hits']['hits']:
                restaurant = {
                    "name": hit['_source']['name'],
                    "category": hit['_source']['category'],
                    "score": round(hit['_score'], 2),
                    "matching_menus": []
                }
                
                # 매칭된 메뉴 정보 추가
                if 'inner_hits' in hit and 'menu' in hit['inner_hits']:
                    for menu_hit in hit['inner_hits']['menu']['hits']['hits']:
                        menu_source = menu_hit['_source']
                        restaurant["matching_menus"].append({
                            "name": menu_source.get('name', ''),
                            "price": menu_source.get('price', '')
                        })
                
                results.append(restaurant)
            
            return {
                "total": response['hits']['total']['value'],
                "results": results,
                "menu_keyword": menu_keyword
            }
            
        except Exception as e:
            return {"error": str(e), "total": 0, "results": []}
    
    def search_by_price_range(
        self, 
        min_price: Optional[int] = None, 
        max_price: Optional[int] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        💰 가격대별 식당/메뉴 검색
        
        Args:
            min_price: 최소 가격 (원)
            max_price: 최대 가격 (원)
            limit: 결과 개수
        
        Returns:
            해당 가격대 메뉴를 제공하는 식당 목록
        """
        try:
            price_conditions = []
            if min_price is not None:
                price_conditions.append({"range": {"menu.price_numeric": {"gte": min_price}}})
            if max_price is not None:
                price_conditions.append({"range": {"menu.price_numeric": {"lte": max_price}}})
            
            if not price_conditions:
                return {"error": "최소 가격 또는 최대 가격 중 하나는 지정해야 합니다.", "total": 0, "results": []}
            
            search_body = {
                "query": {
                    "nested": {
                        "path": "menu",
                        "query": {
                            "bool": {
                                "must": price_conditions
                            }
                        },
                        "inner_hits": {
                            "size": 5,
                            "_source": ["menu.name", "menu.price", "menu.price_numeric"]
                        }
                    }
                },
                "_source": ["name", "category"],
                "size": limit
            }
            
            response = self.es_client.search(index=self.index_name, body=search_body)
            
            results = []
            for hit in response['hits']['hits']:
                restaurant = {
                    "name": hit['_source']['name'],
                    "category": hit['_source']['category'],
                    "score": round(hit['_score'], 2),
                    "price_range_menus": []
                }
                
                # 가격 범위에 맞는 메뉴들
                if 'inner_hits' in hit and 'menu' in hit['inner_hits']:
                    for menu_hit in hit['inner_hits']['menu']['hits']['hits']:
                        menu_source = menu_hit['_source']
                        restaurant["price_range_menus"].append({
                            "name": menu_source.get('name', ''),
                            "price": menu_source.get('price', ''),
                            "price_numeric": menu_source.get('price_numeric', 0)
                        })
                
                results.append(restaurant)
            
            return {
                "total": response['hits']['total']['value'],
                "results": results,
                "min_price": min_price,
                "max_price": max_price
            }
            
        except Exception as e:
            return {"error": str(e), "total": 0, "results": []}
    
    def get_restaurant_details(self, restaurant_name: str) -> Dict[str, Any]:
        """
        🏪 특정 식당의 상세 정보 조회
        
        Args:
            restaurant_name: 식당명
        
        Returns:
            식당의 상세 정보 (메뉴, 가격 등 모든 정보)
        """
        try:
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"name.keyword": restaurant_name}},
                            {"match": {"name": restaurant_name}}
                        ]
                    }
                },
                "size": 1
            }
            
            response = self.es_client.search(index=self.index_name, body=search_body)
            
            if response['hits']['total']['value'] == 0:
                return {"error": "식당을 찾을 수 없습니다.", "restaurant_name": restaurant_name}
            
            hit = response['hits']['hits'][0]
            restaurant = hit['_source']
            
            return {
                "name": restaurant.get('name', ''),
                "category": restaurant.get('category', ''),
                "menu": restaurant.get('menu', []),
                "menu_count": len(restaurant.get('menu', [])),
                "images": restaurant.get('images', []),
                "restaurant_id": restaurant.get('restaurant_id', ''),
                "indexed_at": restaurant.get('indexed_at', ''),
                "score": round(hit['_score'], 2)
            }
            
        except Exception as e:
            return {"error": str(e), "restaurant_name": restaurant_name}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        📊 전체 식당 통계 정보
        
        Returns:
            식당 수, 카테고리별 통계, 메뉴 통계 등
        """
        try:
            # 카테고리별 통계
            category_agg = {
                "aggs": {
                    "categories": {
                        "terms": {
                            "field": "category",
                            "size": 50
                        }
                    }
                },
                "size": 0
            }
            
            category_response = self.es_client.search(index=self.index_name, body=category_agg)
            
            # 전체 식당 및 메뉴 수 계산
            all_restaurants = {
                "query": {"match_all": {}},
                "_source": ["name", "category", "menu"],
                "size": 1000
            }
            
            all_response = self.es_client.search(index=self.index_name, body=all_restaurants)
            
            total_restaurants = len(all_response['hits']['hits'])
            total_menus = sum(len(hit['_source'].get('menu', [])) for hit in all_response['hits']['hits'])
            
            # 카테고리별 통계 정리
            categories = {}
            for bucket in category_response['aggregations']['categories']['buckets']:
                categories[bucket['key']] = bucket['doc_count']
            
            return {
                "total_restaurants": total_restaurants,
                "total_menus": total_menus,
                "average_menus_per_restaurant": round(total_menus / total_restaurants, 1) if total_restaurants > 0 else 0,
                "categories": categories,
                "top_categories": sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def recommend_similar_restaurants(self, restaurant_name: str, limit: int = 5) -> Dict[str, Any]:
        """
        🎯 유사한 식당 추천
        
        Args:
            restaurant_name: 기준 식당명
            limit: 추천 식당 수
        
        Returns:
            유사한 카테고리/메뉴를 가진 식당 목록
        """
        try:
            # 먼저 기준 식당 정보 조회
            base_restaurant = self.get_restaurant_details(restaurant_name)
            if "error" in base_restaurant:
                return base_restaurant
            
            base_category = base_restaurant['category']
            
            # 같은 카테고리의 다른 식당들 검색
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"category": base_category}}
                        ],
                        "must_not": [
                            {"term": {"name.keyword": restaurant_name}}
                        ]
                    }
                },
                "_source": ["name", "category"],
                "size": limit
            }
            
            response = self.es_client.search(index=self.index_name, body=search_body)
            
            recommendations = []
            for hit in response['hits']['hits']:
                recommendations.append({
                    "name": hit['_source']['name'],
                    "category": hit['_source']['category'],
                    "similarity_reason": f"같은 카테고리 ({base_category})"
                })
            
            return {
                "base_restaurant": restaurant_name,
                "base_category": base_category,
                "recommendations": recommendations,
                "total": len(recommendations)
            }
            
        except Exception as e:
            return {"error": str(e), "restaurant_name": restaurant_name}


# 기존 코드와의 호환성을 위한 래퍼 클래스
class RestaurantService:
    def __init__(self, es_host="localhost", es_port=9200):
        self.search_ai = RestaurantSearchAI(es_host=es_host, es_port=es_port)
    
    def execute_search(self, ai_response):
        """AI 판단에 따라 적절한 검색 메소드 실행"""
        action = ai_response.get('action')
        params = ai_response.get('params', {})
        
        if action == 'search_restaurants':
            return self.search_ai.search_restaurants(**params)
        elif action == 'search_by_category':
            return self.search_ai.search_by_category(**params)
        elif action == 'search_by_menu':
            return self.search_ai.search_by_menu(**params)
        elif action == 'search_by_price_range':
            return self.search_ai.search_by_price_range(**params)
        elif action == 'get_restaurant_details':
            return self.search_ai.get_restaurant_details(**params)
        elif action == 'get_statistics':
            return self.search_ai.get_statistics()
        elif action == 'recommend_similar_restaurants':
            return self.search_ai.recommend_similar_restaurants(**params)
        else:
            # 기본 검색 (하위 호환성)
            query = params.get('keyword', params.get('query', '맛집'))
            return self.search_ai.search_restaurants(query=query)