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
**중요 지침:**
- 당신은 여의도 맛집 전문 AI입니다
- 오직 여의도 지역 식당 관련 질문만 처리하세요
- 음식점이 아닌 다른 주제 질문은 거부하세요
- 허위 정보나 추측은 절대 금지입니다

**현재 사용자 질의:** "{user_query}"

**질의 유형 판단:**
1. 여의도 음식점 관련 → 적절한 도구 선택
2. 기타 주제 → 거부 응답

**사용 가능한 도구들:**
1. search_restaurants: 통합 검색 (include_details=true로 설정하여 메뉴/가격 포함)
2. search_by_category: 카테고리별 검색 (중식당, 일식당 등)
3. search_by_menu: 메뉴명으로 검색 (갈비찜, 짬뽕 등)
4. search_by_price_range: 가격대별 검색
5. get_restaurant_details: 특정 식당 상세 정보 (전체 메뉴/가격)
6. get_statistics: 전체 통계
7. recommend_similar_restaurants: 유사 식당 추천

**도구 선택 우선순위:**
1. 구체적 식당명 언급 → get_restaurant_details
2. 메뉴명 검색 → search_by_menu
3. 카테고리 검색 → search_by_category
4. 일반적 질의 → search_restaurants (include_details=true)

여의도 맛집 관련 질의인지 먼저 판단하고, 맞다면 가장 적절한 도구를 선택하세요.
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
            "model": "claude-3-5-sonnet-20241022",  # 최신 Claude 3.5 Sonnet
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
        
        # AI 추론 과정 먼저 추출
        reasoning = self._extract_reasoning(content)
        
        # tool_use 찾기
        for item in content:
            if item.get('type') == 'tool_use':
                action_result = {
                    "action": item['name'],
                    "params": item['input'],
                    "ai_reasoning": reasoning
                }
                return action_result
        
        # tool_use가 없으면 기본 검색
        fallback_result = self._get_fallback_action("기본 검색")
        fallback_result["ai_reasoning"] = reasoning if reasoning else "도구 선택 없음, 기본 검색 사용"
        
        return fallback_result
    
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
        reasoning_parts = []
        for item in content:
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    reasoning_parts.append(text)
        
        if reasoning_parts:
            return ' '.join(reasoning_parts)
        else:
            # 툴 사용 정보라도 보여주기
            for item in content:
                if item.get('type') == 'tool_use':
                    tool_name = item.get('name', '')
                    return f"선택된 도구: {tool_name}"
            return "AI 추론 정보 없음"
    
    def _get_fallback_action(self, user_query):
        """기본 폴백 액션"""
        return {
            "action": "search_restaurants",
            "params": {"query": user_query if user_query else "맛집"},
            "ai_reasoning": "폴백: 통합 검색 사용"
        }
    
    def generate_user_response(self, user_query, search_results, ai_action):
        """검색 결과를 바탕으로 사용자에게 친화적인 응답 생성"""
        
        # 검색 결과가 없는 경우
        if not search_results.get('results') or search_results.get('total', 0) == 0:
            return "죄송합니다. 검색 조건에 맞는 여의도 식당을 찾지 못했습니다. 다른 키워드로 다시 검색해보시겠어요?"
        
        # 응답 생성을 위한 프롬프트
        results_summary = self._format_results_for_prompt(search_results)
        
        prompt = f"""
당신은 여의도 맛집 전문 AI 어시스턴트입니다.

**중요한 제약사항:**
1. 오직 여의도 지역 식당에 대해서만 답변하세요
2. 제공된 검색 결과에 없는 정보는 절대 만들어내지 마세요
3. 음식 관련 질문이 아니면 "여의도 맛집에 대해서만 도움드릴 수 있습니다"라고 답변하세요
4. **메뉴는 반드시 5개 이상 표시하세요 (메뉴명과 가격만, description 제외)**
5. **이미지는 실제 URL을 제공하세요**
6. 허위 정보나 추측성 발언은 금지입니다
7. **최대 2개 식당만 추천하세요**
8. **응답은 1000자 이내로 제한하세요**

**메뉴 표시 규칙:**
- matching_menus가 있으면 먼저 표시
- 부족한 경우 menu 배열에서 추가로 가져와서 총 5개 이상 맞추기
- description은 표시하지 않음 (메뉴명: 가격 형태만)
- 가격 정보가 없으면 "가격 문의" 표시

**사용자 질의:** "{user_query}"

**검색 결과:**
{results_summary}

**답변 템플릿을 정확히 따라 응답하세요:**

🍽️ **여의도 맛집 추천**

검색 결과 총 [숫자]개의 식당을 찾았습니다.

**📍 추천 식당 (상위 2곳):**

1. **[식당명]** ([카테고리])
   **📋 메뉴:**
   - [메뉴명]: [가격]
   - [메뉴명]: [가격]
   - [메뉴명]: [가격]
   - [메뉴명]: [가격]
   - [메뉴명]: [가격]
   **🖼️ 이미지:** [URL1], [URL2]

2. **[식당명]** ([카테고리])
   **📋 메뉴:**
   - [메뉴명]: [가격]
   - [메뉴명]: [가격]
   - [메뉴명]: [가격]
   - [메뉴명]: [가격]
   - [메뉴명]: [가격]
   **🖼️ 이미지:** [URL1], [URL2]

**💡 추가 도움:**
특정 메뉴나 가격대를 원하시면 말씀해주세요.

**중요: 2개 식당, 각각 5개 메뉴, 이미지 2개씩, 1000자 이내로 간결하게!**
"""

        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.claude_api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 800,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = requests.post(
                self.claude_api_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('content', [])
                
                for item in content:
                    if item.get('type') == 'text':
                        return item.get('text', '').strip()
            
            # API 호출 실패 시 기본 응답
            return self._generate_default_response(user_query, search_results)
            
        except Exception as e:
            print(f"응답 생성 오류: {e}")
            return self._generate_default_response(user_query, search_results)
    
    def _format_results_for_prompt(self, search_results):
        """검색 결과를 프롬프트용으로 포맷팅 (메뉴, 가격, 이미지 URL 포함)"""
        results = search_results.get('results', [])
        total = search_results.get('total', 0)
        
        formatted = f"총 {total}개 식당 검색됨\n\n"
        
        for i, restaurant in enumerate(results[:4], 1):  # 상위 4개 (검색 결과 처리용)
            name = restaurant.get('name', '')
            category = restaurant.get('category', '')
            
            formatted += f"{i}. 식당명: {name}\n"
            formatted += f"   카테고리: {category}\n"
            
            # 이미지 URL 상세히 포함
            images = restaurant.get('images', [])
            if images:
                formatted += f"   이미지 URL ({len(images)}개):\n"
                for idx, img in enumerate(images[:3], 1):  # 상위 3개 이미지 URL
                    img_url = img.get('url', '')
                    img_alt = img.get('alt', '이미지')
                    formatted += f"     {idx}. {img_alt}: {img_url}\n"
            else:
                formatted += f"   이미지: 없음\n"
            
            # 메뉴 정보 상세히 포함 (최소 5개 + description)
            if 'matching_menus' in restaurant and restaurant['matching_menus']:
                formatted += f"   매칭된 메뉴:\n"
                for menu in restaurant['matching_menus'][:5]:  # 상위 5개 메뉴
                    menu_name = menu.get('name', '정보없음')
                    menu_price = menu.get('price', '가격정보없음')
                    menu_desc = menu.get('description', '설명없음')
                    formatted += f"     - {menu_name}: {menu_price} (설명: {menu_desc})\n"
            elif 'menu' in restaurant and restaurant['menu']:
                formatted += f"   주요 메뉴 (최소 5개):\n"
                for menu in restaurant['menu'][:5]:  # 상위 5개 메뉴
                    menu_name = menu.get('name', '정보없음')
                    menu_price = menu.get('price', '가격정보없음')
                    menu_desc = menu.get('description', '설명없음')
                    formatted += f"     - {menu_name}: {menu_price} (설명: {menu_desc})\n"
            else:
                formatted += f"   메뉴: 상세 정보가 필요한 경우 식당명으로 검색 요청\n"
            
            formatted += "\n"
        
        return formatted
    
    def _generate_default_response(self, user_query, search_results):
        """기본 응답 생성 (AI API 실패 시) - 템플릿 적용"""
        results = search_results.get('results', [])
        total = search_results.get('total', 0)
        
        if total == 0:
            return "🍽️ **여의도 맛집 검색 결과**\n\n죄송합니다. 검색 조건에 맞는 여의도 식당을 찾지 못했습니다.\n\n💡 다른 키워드로 다시 검색해보시거나, '맛집 추천'으로 검색해보세요."
        
        # 템플릿 적용
        response = f"🍽️ **여의도 맛집 추천**\n\n안녕하세요! 검색 결과 총 {total}개의 식당을 찾았습니다.\n\n**📍 추천 식당:**\n\n"
        
        for i, restaurant in enumerate(results[:2], 1):
            name = restaurant.get('name', '')
            category = restaurant.get('category', '')
            images = restaurant.get('images', [])
            
            response += f"{i}. **{name}** ({category})\n"
            response += f"**📋 메뉴:**\n"
            
            # 메뉴 정보 포함 (최소 5개, description 없이)
            menu_count = 0
            if 'matching_menus' in restaurant and restaurant['matching_menus']:
                for menu in restaurant['matching_menus'][:5]:
                    menu_name = menu.get('name', '')
                    menu_price = menu.get('price', '')
                    if menu_name:
                        response += f"   - {menu_name}: {menu_price}\n"
                        menu_count += 1
            elif 'menu' in restaurant and restaurant['menu']:
                for menu in restaurant['menu'][:5]:
                    menu_name = menu.get('name', '')
                    menu_price = menu.get('price', '')
                    if menu_name:
                        response += f"   - {menu_name}: {menu_price}\n"
                        menu_count += 1
            
            if menu_count == 0:
                response += f"   - 메뉴 정보: 식당명으로 상세 검색 가능\n"
            
            # 이미지 URL 정보 한 줄로 압축
            response += f"**🖼️ 이미지:** "
            if images:
                img_urls = []
                for img in images[:3]:
                    img_url = img.get('url', '')
                    if img_url:
                        img_urls.append(img_url)
                if img_urls:
                    response += ", ".join(img_urls) + "\n"
                else:
                    response += "이미지 없음\n"
            else:
                response += "이미지 없음\n"
            
            response += "\n"
        
        response += "**💡 추가 도움:**\n"
        response += "- 특정 메뉴나 가격대를 원하시면 말씀해주세요\n"
        response += "- 식당 상세 정보가 필요하면 식당명을 알려주세요\n\n"
        response += "**주의:** 실제 방문 전 영업시간과 메뉴 확인을 권장드립니다."
        
        return response
