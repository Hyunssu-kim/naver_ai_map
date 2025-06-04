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
        
        # AI에게 사용자 질의 분석 요청
        ai_response = ai_service.analyze_query(user_query)
        
        # AI 판단에 따른 메소드 호출
        result = restaurant_service.execute_search(ai_response)
        
        return create_response(200, {
            'query': user_query,
            'result': result
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {'error': '서버 오류가 발생했습니다'})