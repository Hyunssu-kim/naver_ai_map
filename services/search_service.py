# Elasticsearch 연결 템플릿 - 실제 연결 코드로 교체하세요

class ElasticsearchService:
    def __init__(self):
        # TODO: EC2 Elasticsearch 연결 설정
        # self.es = Elasticsearch([{'host': 'your-ec2-ip', 'port': 9200}])
        self.index_name = "yeouido_restaurants"
    
    def search(self, query):
        """엘라스틱서치 검색 - TEMP"""
        # TODO: 실제 ES 검색 구현
        # result = self.es.search(index=self.index_name, body=query)
        # return self._format_results(result)
        
        # 임시 더미 데이터
        return {
            "total": 3,
            "restaurants": [
                {
                    "id": "1",
                    "name": "여의도 한정식",
                    "food_type": "한식",
                    "rating": 4.5,
                    "address": "여의도동 123-45",
                    "phone": "02-1234-5678"
                },
                {
                    "id": "2", 
                    "name": "IFC 이탈리안",
                    "food_type": "이탈리안",
                    "rating": 4.2,
                    "address": "여의도동 IFC몰 3층",
                    "phone": "02-2345-6789"
                }
            ]
        }
    
    def get_by_id(self, restaurant_id):
        """ID로 맛집 조회 - TEMP"""
        # TODO: 실제 ES get 구현
        # return self.es.get(index=self.index_name, id=restaurant_id)
        
        return {
            "id": restaurant_id,
            "name": "여의도 맛집",
            "description": "맛있는 음식점입니다",
            "rating": 4.3,
            "reviews": ["맛있어요", "서비스 좋아요"]
        }
    
    def _format_results(self, es_result):
        """ES 결과 포맷팅"""
        return {
            "total": es_result['hits']['total']['value'],
            "restaurants": [hit['_source'] for hit in es_result['hits']['hits']]
        }