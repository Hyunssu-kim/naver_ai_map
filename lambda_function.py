import json
import boto3
from services.ai_service import AIService
from services.restaurant_service import RestaurantService
from utils.response_handler import create_response

def lambda_handler(event, context):
    try:
        # 요청 파싱
        body = json.loads(event['body']) if 'body' in event else event
        user_query = body.get('query', '')
        
        if not user_query:
            return create_response(400, {'error': '질의가 필요합니다'})
        
        # AI 서비스 초기화
        ai_service = AIService()
        restaurant_service = RestaurantService()
        
        print(f"사용자 질의: {user_query}")
        
        # AI에게 사용자 질의 분석 요청 (재시도 로직 포함)
        ai_response = ai_service.analyze_query(user_query)
        
        print(f"AI 선택 액션: {ai_response.get('action')}")
        print(f"AI 추론: {ai_response.get('ai_reasoning', 'N/A')}")
        
        # AI 판단에 따른 메소드 호출
        search_results = restaurant_service.execute_search(ai_response)
        
        # 검색 결과 검증
        validation = ai_service.validate_search_results(search_results, user_query)
        
        # 만족스럽지 않은 결과면 대안 검색 수행
        if not validation.get('is_satisfactory', True):
            print(f"검색 결과 불만족: {validation.get('suggestion')}")
            
            alternative_action = validation.get('alternative_action')
            if alternative_action:
                print(f"대안 검색 수행: {alternative_action.get('action')}")
                search_results = restaurant_service.execute_search(alternative_action)
        
        # 최종 응답 생성
        response_data = {
            'query': user_query,
            'ai_action': ai_response.get('action'),
            'ai_reasoning': ai_response.get('ai_reasoning', ''),
            'result': search_results,
            'validation': validation.get('suggestion', ''),
            'total_found': search_results.get('total', 0)
        }
        
        return create_response(200, response_data)
        
    except Exception as e:
        print(f"Lambda Error: {str(e)}")
        return create_response(500, {
            'error': '서버 오류가 발생했습니다',
            'details': str(e)
        })