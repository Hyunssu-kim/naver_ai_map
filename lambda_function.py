import json
import boto3
from services.ai_service import AIService
from services.restaurant_service import RestaurantService
from utils.response_handler import create_response

def lambda_handler(event, context):
    try:
        body = json.loads(event['body']) if 'body' in event else event
        user_query = body.get('query', '')
        conversation_id = body.get('conversation_id', None)  # 대화 ID (선택사항)
        
        if not user_query:
            return create_response(400, {'error': '질의가 필요합니다'})

        ai_service = AIService()
        restaurant_service = RestaurantService()

        ai_response = ai_service.analyze_query(user_query, conversation_id)

        search_results = restaurant_service.execute_search(ai_response)

        user_friendly_response = ai_service.generate_user_response(
            user_query, search_results, ai_response.get('action')
        )

        response_data = {
            'answer': user_friendly_response,
            'search_results': search_results
        }
        
        return create_response(200, response_data)
        
    except Exception as e:
        print(f"Lambda Error: {str(e)}")
        return create_response(500, {
            'error': '서버 오류가 발생했습니다',
            'details': str(e)
        })