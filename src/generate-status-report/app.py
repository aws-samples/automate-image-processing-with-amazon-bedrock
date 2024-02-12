import boto3
import os
import json

STATUS_TABLE = os.environ.get('STATUS_TABLE')
STATUS_REPORT_URL_EXPIRATION = os.environ.get('STATUS_REPORT_URL_EXPIRATION')

ddb_client = boto3.resource("dynamodb").Table(STATUS_TABLE)

s3_client = boto3.client('s3')

def lambda_handler(event, context):

    print(event)
    
    #Fetch request payload
    status_id = event['Id']
    s3_bucket = event['S3Bucket']
    status_s3_prefix = event['StatusS3Prefix']

    try:
        
        status = fetch_status_details(status_id)
        
        status_json = json.dumps(status, indent=2)
        report_file_name = f'status_report_{status_id}.json'
        report_file_s3_key = f'{status_s3_prefix}/{report_file_name}'
        
        #upload Json file to s3 and generate a pre-signed url
        s3_client.put_object(Body=status_json, Bucket=s3_bucket, Key=report_file_s3_key)
        
        url = s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': s3_bucket,
                    'Key': report_file_s3_key,
                },
                ExpiresIn=STATUS_REPORT_URL_EXPIRATION
        )    
        
        return {
            'StatusCode': 200,
            'Url': url
        }        

    except Exception as e:
        print('Error in generating report')
        print(e)

# Write a python method to fetch id, imagename, status, cause and error from StableTable DynamoDB table for the provided id
def fetch_status_details(id):
    
    response = ddb_client.query(
            KeyConditionExpression='Id = :id',
            ExpressionAttributeValues={':id': id}
        )
        
    items = response.get('Items')
    
    return items