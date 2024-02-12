import boto3
import os
import json
import base64
import io
from PIL import Image, ImageDraw

s3_client = boto3.client('s3')

def lambda_handler(event, context):

    print(event)
    
    #Fetch request payload
    s3_bucket = event['S3Bucket']
    output_s3_prefix = event['OutputS3Prefix']
    image_file_name = event['Image']['ImageName']
    image_file_name_without_extension = image_file_name.split('.')[0]
    s3_output_key = f'{output_s3_prefix}/{image_file_name_without_extension}.json'
    # Path to store images files in temporary storage
    tmp_output_path = f'/tmp/generated_{image_file_name}'

    try:
        
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_output_key)
        json_response = json.loads(response['Body'].read().decode('utf-8'))
        
        # Loop through the generated images and save each to disk.
        images = json_response["images"]
        image_data = images[0]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        image.save(tmp_output_path)

        print(f"Transformed image saved as {tmp_output_path}")
        
        #upload image
        s3_client.upload_file(tmp_output_path, s3_bucket, f'{output_s3_prefix}/{image_file_name}')
        
    
    except Exception as e:
        print('Error in parsing response')
        print(e)

    finally:
        if os.path.exists(tmp_output_path):
            os.remove(tmp_output_path)



