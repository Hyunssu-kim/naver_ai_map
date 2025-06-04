import boto3
import json
from utils.tools import RESTAURANT_TOOLS

class AIService:
    def __init__(self):
        # Bedrock 클라이언트 (Claude 사용)
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
    def analyze_query(self, user_query):
        """사용자 질의를 분석하여 적절한 메소드 결정"""
        
        prompt = f"""
사용자 질의: "{user_query}"

여의도 맛집 검색을 위해 다음 도구들 중 가장 적절한 것을 선택해주세요:

1. search_restaurants: 통합 검색 (식당명, 카테고리, 메뉴명으로 검색)
2. search_by_category: 카테고리별 검색 (중식당, 일식당 등)
3. search_by_menu: 메뉴명으로 검색 (갈비찜, 짬뽕 등)
4. search_by_price_range: 가격대별 검색
5. get_restaurant_details: 특정 식당 상세 정보
6. get_statistics: 전체 통계
7. recommend_similar_restaurants: 유사 식당 추천

사용자 질의를 분석하고 가장 적절한 도구를 사용해주세요.
"""
        
        try:
            # Claude API 호출 (Bedrock)
            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "tools": RESTAURANT_TOOLS
                })
            )
            
            result = json.loads(response['body'].read())
            return self._parse_ai_response(result)
            
        except Exception as e:
            print(f"AI Service Error: {e}")
            # 기본 검색으로 폴백
            return {
                "action": "search_restaurants",
                "params": {"query": user_query}
            }
    
    def _parse_ai_response(self, ai_result):
        """AI 응답을 파싱하여 실행할 액션 결정"""
        # AI 응답에서 tool_use 추출
        content = ai_result.get('content', [])
        
        for item in content:
            if item.get('type') == 'tool_use':
                return {
                    "action": item['name'],
                    "params": item['input']
                }
        
        # 기본값 - 통합 검색 사용
        return {
            "action": "search_restaurants", 
            "params": {"query": "맛집"}
        }