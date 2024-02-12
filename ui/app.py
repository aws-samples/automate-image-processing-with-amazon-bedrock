import streamlit as st
import boto3
from htmlTemplates import css, bot_template, user_template
import os
import config
import requests
import json
from PIL import Image
from io import BytesIO
from streamlit_cognito_auth import CognitoAuthenticator
from datetime import datetime
import base64
import uuid

s3 = boto3.client('s3')

st.set_page_config(page_title="Image Processing", page_icon=":books::parrot:", layout="wide")

st.write(css, unsafe_allow_html=True)
st.markdown("""
        <style>
              .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                }
        </style>
        """, unsafe_allow_html=True)
    


if 'clicked' not in st.session_state:
    st.session_state.clicked = False

if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0
    
pool_id = config.COGNITO_POOL_ID
app_client_id = config.COGNITO_POOL_CLIENT
app_client_secret = config.COGNITO_POOL_CLIENT_SECRET

authenticator = CognitoAuthenticator(
    pool_id=pool_id,
    app_client_id=app_client_id,
    app_client_secret=app_client_secret,
)


is_logged_in = authenticator.login()
if not is_logged_in:
    st.stop()  

def logout():
    authenticator.logout()
    
col1, col2, col3 = st.columns([120, 100, 20])

with col3:
    st.button("Logout", "logout_btn", on_click=logout)


#Upload image file to S3 bucket 
def upload_image_to_S3(image_file,datetime_prefix, image_file_name):

    try:
        s3.upload_fileobj(image_file, config.IMAGE_BUCKET, f'{config.IMAGE_PREFIX}/{datetime_prefix}/{image_file_name}')
        return True
    except FileNotFoundError:
        st.error('File not found.')
        return False  
        

#Detect labels from image and display in streamlit for user to select
def detect_labels(image_data):
    
    # Invokde API to detect labels
    api_gateway_endpoint = f'{config.API_GATEWAY_ENDPOINT}/detectLabels'
    cognito_id_token = st.session_state.auth_id_token 
    headers = {'Authorization': f'Bearer {cognito_id_token}'}
    base64_string = image_data.decode('utf-8')
    data = {'Image': {'Bytes': base64_string}}
    response = requests.post(api_gateway_endpoint, headers=headers, json=data)
    response = response.json()
    
    labels = []

    for label in response['Labels']:
        if len(label['Instances']) >0 :
            labels.append(label["Name"])
    
    return labels

#Insert images details to DynamoDB
def submit_images(datetime_prefix, prompt, negative_prompt,mode, images):
    
    id = f'{uuid.uuid4()}'
    
    # Invokde API to detect labels
    api_gateway_endpoint = f'{config.API_GATEWAY_ENDPOINT}/images'
    cognito_id_token = st.session_state.auth_id_token 
    headers = {'Authorization': f'Bearer {cognito_id_token}'}

    data = {
                "Id": id,
                "ImageS3Prefix": f'/{datetime_prefix}',
                "Prompt": prompt,
                "NegativePrompt": negative_prompt,
                "Mode": mode,
                "Images":images
    }
    
    response = requests.post(api_gateway_endpoint, headers=headers, json=data)
    response = response.json()



def submit():
    st.session_state.clicked = True  


uploaded_images = st.file_uploader("Select one or more image file(s). The image width and height must both be 1024 pixels or less.", ['png', 'jpg'], accept_multiple_files=True, key=f'file_uploade_key_{st.session_state["file_uploader_key"]}')    

image_index = 0

images = []


cols_index = 0

image_placeholder = st.empty()

with image_placeholder.container():
    cols = st.columns(4)
    if uploaded_images is not None:
        for uploaded_image in uploaded_images:
            if uploaded_image is not None:
                image_data = base64.b64encode(uploaded_image.getvalue())
                # Display labels
                labels = detect_labels(image_data)
                cols[cols_index].image(uploaded_image)
                selected_labels = cols[cols_index].multiselect(uploaded_image.name, labels, default=labels, key=image_index)
                selected_labels_images = {}
                selected_labels_images["ImageName"] = uploaded_image.name
                selected_labels_images["Labels"] = ", ".join(selected_labels)
                images.append(selected_labels_images)
                image_index = image_index + 1
                if cols_index == 3:
                    cols_index = 0
                else:
                    cols_index = cols_index + 1
                    
with st.sidebar.form("process_images"):
    prompt = st.text_area("Prompt:", help="A text prompt to define what to change in the background.")
    negative_prompt = st.text_area("Negative prompt:", help="A text prompt to define what not to include in the image.")
    outpainting_mode = st.selectbox("Mode", ("DEFAULT","PRECISE"), help="DEFAULT – Use this option to allow modification of the image inside the mask in order to keep it consistent with the reconstructed background.  \n PRECISE – Use this option to prevent modification of the image inside the mask.")
    st.caption("Generated images size: 1024 X 1024")
    
    #st.button("Submit", on_click=submit) 
    submitted = st.form_submit_button("Submit")
    if submitted:
        
        with st.spinner('Submitting for image processing...'):
            
            try:
                if uploaded_images is not None:
                    datetime_prefix = datetime.now().strftime("%Y/%m/%d/%H:%M:%S")
                    for uploaded_image in uploaded_images:
                        if uploaded_image is not None:
                            # Upload image to S3
                            upload_image_to_S3(uploaded_image, datetime_prefix, uploaded_image.name)
                        
                    submit_images(datetime_prefix,prompt, negative_prompt,outpainting_mode, images)
                    st.success("Images submitted successfully for further processing.", icon="✅")
                    uploaded_images.clear()
                    images.clear()
                    image_placeholder.empty()
                    
                    st.session_state.clicked = False
    
                    st.session_state["file_uploader_key"] += 1
                    st.rerun()
                    
            except Exception as e:
                st.error("Error Occured.", icon="🚨")
                st.error(e)
                raise        


