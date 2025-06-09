class ElasticsearchService:
    def __init__(self):

        self.secrets_client = boto3.client('secretsmanager')
        elastic_config = self._get_elastic_config()
        self.es_client = Elasticsearch(
            f"http://{elastic_config['host']}:{elastic_config.get('port', 9200)}",
            http_auth=(elastic_config['username'], elastic_config['password'])
        )
        self.index_name = "restaurants"

    def _get_elastic_config(self):
        response = self.secrets_client.get_secret_value(
            SecretId='my_dev_key'
        )
        secret = json.loads(response['SecretString'])

        required_fields = ['elastic_ip', 'elastic_port', 'elastic_username', 'elastic_password']
        for field in required_fields:
            if not secret.get(field):
                raise ValueError(f"Secret에서 {field}를 찾을 수 없습니다")

        elastic_config = {
            'host': secret['elastic_ip'],
            'port': secret.get('elastic_port', 9200),
            'username': secret['elastic_username'],
            'password': secret['elastic_password']
        }
        return elastic_config

    def search(self, query):
        """엘라스틱서치 검색 - TEMP"""
        # TODO: 실제 ES 검색 구현
        result = self.es.search(index=self.index_name, body=query)
        return self._format_results(result)

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


    def _format_results(self, es_result):
        """ES 결과 포맷팅"""
        return {
            "total": es_result['hits']['total']['value'],
            "restaurants": [hit['_source'] for hit in es_result['hits']['hits']]
        }