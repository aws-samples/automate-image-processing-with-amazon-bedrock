import boto3
import os
import json
import base64
import io
from random import randint

s3_client = boto3.client('s3')

def lambda_handler(event, context):

    print(event)
    
    #Fetch request payload
    s3_bucket = event['S3Bucket']
    input_s3_prefix = event['InputS3Prefix']
    prompt = event['Prompt']
    negative_prompt = event['NegativePrompt']
    mode = event['Mode']
    image_file_name = event['Image']['ImageName']
    image_labels = event['Image']['Labels']
    
    image_file_uri = f"s3://{s3_bucket}/{input_s3_prefix}/{image_file_name}"
    image_file_name_without_extension = image_file_name.split('.')[0]
    
    # Path to store images files in temporary storage
    tmp_image_path = f'/tmp/{image_file_name}'
    
    s3_output_key = f'{input_s3_prefix}/{image_file_name_without_extension}.json'

    try:
        
        s3_client.download_file(s3_bucket, f'{input_s3_prefix}/{image_file_name}', tmp_image_path)    
        
        # Convert images to base64 encoded strings
        image_base64 = image_to_base64(tmp_image_path)
        
        # Build Bedrock request
        request_payload = {
            "taskType": "OUTPAINTING",
            "outPaintingParams": {
                "image": image_base64,
                "text": prompt,
                "negativeText": negative_prompt,
                "maskPrompt": image_labels,
                "outPaintingMode": mode,
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "premium",
                "height": 1024,
                "width": 1024,
                "cfgScale": 8.0,
                "seed": randint(0, 100000),
            }
        }        
        
        request_payload_string = json.dumps(request_payload)
        
        #upload image
        s3_client.put_object(Body=request_payload_string, Bucket=s3_bucket, Key=s3_output_key)
        

    except Exception as e:
        print('Error in building request')
        print(e)

    finally:
        if os.path.exists(tmp_image_path):
            os.remove(tmp_image_path)


def image_to_base64(img_path) -> str:
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


