import boto3
import json
import requests
from utils.tools import RESTAURANT_TOOLS

class AIService:
    def __init__(self):
        # AWS Secrets Manager에서 Claude API 키 가져오기
        self.secrets_client = boto3.client('secretsmanager')
        self.claude_api_key = self._get_claude_api_key()
        self.claude_api_url = "https://api.anthropic.com/v1/messages"
        
        # 재시도 설정
        self.max_retries = 3
        self.min_results_threshold = 2  # 최소 결과 개수
        
    def _get_claude_api_key(self):
        """AWS Secrets Manager에서 Claude API 키 가져오기"""
        try:
            response = self.secrets_client.get_secret_value(
                SecretId='my_dev_key'  # Secret 이름
            )
            secret = json.loads(response['SecretString'])
            return secret.get('api_key')
        except Exception as e:
            print(f"API Key 조회 실패: {e}")
            raise e
    
    def analyze_query(self, user_query):
        """사용자 질의를 분석하여 적절한 메소드 결정 (재시도 로직 포함)"""
        
        for attempt in range(self.max_retries):
            try:
                print(f"AI 분석 시도 {attempt + 1}/{self.max_retries}")
                
                # Claude API 호출
                ai_response = self._call_claude_api(user_query, attempt)
                action_result = self._parse_ai_response(ai_response)
                
                # 결과 검증 및 재시도 판단
                should_retry, retry_reason = self._should_retry_search(
                    action_result, user_query, attempt
                )
                
                if not should_retry:
                    return action_result
                else:
                    print(f"재시도 이유: {retry_reason}")
                    continue
                    
            except Exception as e:
                print(f"AI 분석 오류 (시도 {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    # 마지막 시도 실패 시 기본 검색
                    return self._get_fallback_action(user_query)
        
        # 모든 시도 실패 시 기본 검색
        return self._get_fallback_action(user_query)
    
    def _call_claude_api(self, user_query, attempt):
        """Claude API 직접 호출"""
        
        # 시도 횟수에 따른 프롬프트 조정
        base_prompt = f"""
사용자 질의: "{user_query}"

중요: 이 시스템은 여의도 맛집 검색 전용입니다. 여의도 음식점/식당/맛집과 관련되지 않은 질문에는 응답하지 마세요.

여의도 맛집 검색을 위해 가장 적절한 도구를 선택해주세요.

사용 가능한 도구들:
1. search_restaurants: 통합 검색 (식당명, 카테고리, 메뉴명으로 검색)
2. search_by_category: 카테고리별 검색 (중식당, 일식당 등)
3. search_by_menu: 메뉴명으로 검색 (갈비찜, 짬뽕 등)
4. search_by_price_range: 가격대별 검색
5. get_restaurant_details: 특정 식당 상세 정보
6. get_statistics: 전체 통계
7. recommend_similar_restaurants: 유사 식당 추천

사용자 질의를 분석하고 가장 적절한 도구를 사용해주세요.
"""
        
        if attempt > 0:
            base_prompt += f"""

[재시도 {attempt + 1}번째]
이전 시도에서 만족스럽지 않은 결과가 나왔습니다. 
다른 접근 방식이나 더 넓은 검색 범위를 고려해주세요.
예: 구체적인 검색어 → 일반적인 검색어, 카테고리별 → 통합검색 등
"""

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.claude_api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": base_prompt
                }
            ],
            "tools": RESTAURANT_TOOLS
        }
        
        response = requests.post(
            self.claude_api_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API 오류: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _parse_ai_response(self, ai_result):
        """AI 응답을 파싱하여 실행할 액션 결정"""
        content = ai_result.get('content', [])
        
        for item in content:
            if item.get('type') == 'tool_use':
                return {
                    "action": item['name'],
                    "params": item['input'],
                    "ai_reasoning": self._extract_reasoning(content)
                }
        
        # tool_use가 없으면 기본 검색
        return self._get_fallback_action("기본 검색")
    
    def _should_retry_search(self, action_result, user_query, attempt):
        """검색 결과를 바탕으로 재시도 여부 결정"""
        
        # 마지막 시도면 재시도 안함
        if attempt >= self.max_retries - 1:
            return False, "최대 재시도 횟수 도달"
        
        # 액션 결과가 없으면 재시도
        action = action_result.get('action')
        params = action_result.get('params', {})
        
        if not action:
            return True, "유효한 액션이 선택되지 않음"
        
        # 특정 조건들 검사
        retry_conditions = [
            # 검색어가 너무 구체적인 경우
            self._is_query_too_specific(user_query, action, params),
            # 가격 검색인데 가격 정보가 부족한 경우
            self._is_price_search_problematic(action, params),
            # 특정 식당 검색인데 존재하지 않을 가능성이 높은 경우
            self._is_specific_restaurant_risky(action, params, user_query)
        ]
        
        for should_retry, reason in retry_conditions:
            if should_retry:
                return True, reason
        
        return False, "재시도 불필요"
    
    def _is_query_too_specific(self, user_query, action, params):
        """검색어가 너무 구체적인지 확인"""
        if action == 'get_restaurant_details':
            # 매우 구체적인 식당명이지만 존재하지 않을 수 있음
            restaurant_name = params.get('restaurant_name', '')
            if len(restaurant_name) > 15 or '맛집' in restaurant_name:
                return True, "너무 구체적인 식당명 검색"
        
        return False, ""
    
    def _is_price_search_problematic(self, action, params):
        """가격 검색이 문제가 될 수 있는지 확인"""
        if action == 'search_by_price_range':
            min_price = params.get('min_price')
            max_price = params.get('max_price')
            
            # 너무 좁은 가격 범위
            if min_price and max_price and (max_price - min_price) < 5000:
                return True, "가격 범위가 너무 좁음"
            
            # 너무 높은 가격
            if min_price and min_price > 50000:
                return True, "가격대가 너무 높음"
        
        return False, ""
    
    def _is_specific_restaurant_risky(self, action, params, user_query):
        """특정 식당 검색이 위험한지 확인"""
        if action == 'get_restaurant_details':
            # 일반적인 질의인데 특정 식당 검색으로 해석된 경우
            general_keywords = ['맛집', '추천', '찾아', '어디', '뭐가']
            if any(keyword in user_query for keyword in general_keywords):
                return True, "일반적인 질의인데 특정 식당 검색으로 해석됨"
        
        return False, ""
    
    def _extract_reasoning(self, content):
        """AI의 추론 과정 추출"""
        for item in content:
            if item.get('type') == 'text':
                return item.get('text', '')
        return ""
    
    def _get_fallback_action(self, user_query):
        """기본 폴백 액션"""
        return {
            "action": "search_restaurants",
            "params": {"query": user_query if user_query else "맛집"},
            "ai_reasoning": "폴백: 통합 검색 사용"
        }
    
    def validate_search_results(self, search_results, original_query):
        """검색 결과 검증 및 개선 제안"""
        
        if not search_results or search_results.get('total', 0) == 0:
            return {
                "is_satisfactory": False,
                "suggestion": "검색 결과가 없습니다. 더 일반적인 키워드로 다시 검색해보세요.",
                "alternative_action": {
                    "action": "search_restaurants",
                    "params": {"query": "맛집", "limit": 10}
                }
            }
        
        total_results = search_results.get('total', 0)
        
        if total_results < self.min_results_threshold:
            return {
                "is_satisfactory": False,
                "suggestion": f"검색 결과가 {total_results}개로 적습니다. 더 넓은 범위로 검색하겠습니다.",
                "alternative_action": {
                    "action": "search_restaurants",
                    "params": {"query": original_query, "limit": 15}
                }
            }
        
        return {
            "is_satisfactory": True,
            "suggestion": "만족스러운 검색 결과입니다."
        }