import boto3
import os
import json

step_function = boto3.client("stepfunctions")

STATE_MACHINE_IMAGE_PROCESSING_ARN = os.environ.get('STATE_MACHINE_IMAGE_PROCESSING_ARN')
INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
IMAGE_PREFIX = os.environ.get('IMAGE_PREFIX')
GENERATED_IMAGE_PREFIX = os.environ.get('GENERATED_IMAGE_PREFIX')
STATUS_REPORT_PREFIX = os.environ.get('STATUS_REPORT_PREFIX')

def lambda_handler(event, context):
    try:
        
        print('Starting image processing workflow')    
        dynamodb_item = event['Records'][0]['dynamodb']

        record = {}
        
        record['Id'] = dynamodb_item['NewImage']['Id']['S']
        image_s3_prefix = dynamodb_item['NewImage']['ImageS3Prefix']['S']
        record['S3Bucket'] = INPUT_BUCKET
        record['InputS3Prefix'] = f'{IMAGE_PREFIX}{image_s3_prefix}'
        record['OutputS3Prefix'] = f'{GENERATED_IMAGE_PREFIX}{image_s3_prefix}'
        record['StatusS3Prefix'] = f'{STATUS_REPORT_PREFIX}{image_s3_prefix}'
        record['Prompt'] = dynamodb_item['NewImage']['Prompt']['S']        
        record['NegativePrompt'] = dynamodb_item['NewImage']['NegativePrompt']['S']
        record['Mode'] = dynamodb_item['NewImage']['Mode']['S']
        
        dynamodb_item_images = dynamodb_item['NewImage']['Images']['L']
        images_list = []
        
        
        for image in dynamodb_item_images:
            image_info = {
                'ImageName': image['M']['ImageName']['S'],
                'Labels': image['M']['Labels']['S']
            }
            images_list.append(image_info)
            
        
        record['Images'] = images_list
            
        record = json.dumps(record)
        #print(record)
        
        
        step_function.start_execution(
            
            stateMachineArn=STATE_MACHINE_IMAGE_PROCESSING_ARN,
            input=record,

        )
        
        return True
        
    except Exception as e:
        print(f"Error in starting workflow: {str(e)}")
        

