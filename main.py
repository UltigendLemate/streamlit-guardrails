import streamlit as st
import requests
import json
import os


api_key = st.secrets["API_KEY"]

# Define functions to interact with the APIs
def get_response(prompt):
    url = "https://api.hyperleap.ai/conversations/e4f55a1c-122f-45ea-9ceb-2b09a07674de/continue-sync"
    payload = json.dumps({"message": prompt})
    headers = {
        "accept": "application/json",
        "x-hl-api-key": api_key,
        "content-type": "application/json"
    }
    response = requests.patch(url, data=payload, headers=headers)
    result = response.json()
    return result

def send_for_moderations(message):
    url = "https://api.hyperleap.ai/moderations"
    payload = json.dumps({"input": message})
    headers = {
        "x-hl-api-key": api_key,
        "content-type": "application/json"
    }
    response = requests.post(url, data=payload, headers=headers)
    result = response.json()
    return result

def detect_topic(message):
    url = "https://api.hyperleap.ai/prompts"
    payload = {
    "promptId": "2f654e34-637f-466c-96ab-ed0722a39ccb",
    "replacements": {
        "topics": topics_value,
        "message": message
        }
    }
    headers = {
        "accept": "application/json",
        "x-hl-api-key":api_key,
        "content-type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    result = response.json()
    print("result of topic ",result)
    result = result['choices'][0]['message']['content']
    return result

def detect_toxicity(message):
    url = "https://api.hyperleap.ai/prompts"
    payload = {
        "promptId": "fc4ef70d-2889-4357-831f-f7e9f5f19849",
        "replacements": {
            "input": message
        }
    }
    headers = {
        "accept": "application/json",
        "x-hl-api-key": api_key,
        "content-type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    result = response.json()
    print("result of toxic ",result)
    result = result['choices'][0]['message']['content']
    return result


def process_response(response):
    errors = []
    if topics_checkbox:
        print('topic check')
        topic_detection = detect_topic(prompt)
        if topic_detection.lower()=="true":
            errors.append("derogatory topics")
        print(topic_detection)
    
    if st.session_state['checkbox_states']['Toxicity']:
        print('toxicity check')
        toxicity_detection = detect_toxicity(prompt)
        if toxicity_detection.lower()=="true":
            errors.append("toxicity")
        print(toxicity_detection)

    if keyword_checkbox:
        print('keyword check')
        keywords = keyword_value.split(",")
        flag = False
        for keyword in keywords:
            if keyword.lower() in response.lower():
                flag = True
                break
        if flag : 
            errors.append("derogatory keywords")

    if any(st.session_state['checkbox_states'].values()) :
        print("moderation")
        result = send_for_moderations(response)
        flagged_categories = [
            category.lower() for category, is_flagged in result["results"][0]["categories"].items() if is_flagged
        ]
        normalized_flagged_categories = set()
        for category in flagged_categories:
            if "hate" in category:
                normalized_flagged_categories.add("hate")
            elif "harassment" in category:
                normalized_flagged_categories.add("harassment")
            else:
                normalized_flagged_categories.add(category)
        selected_categories = [
            category.lower() for category, selected in st.session_state['checkbox_states'].items() if selected
        ]
        matching_categories = list(set(normalized_flagged_categories) & set(selected_categories))
        print(normalized_flagged_categories)
        errors = errors + matching_categories

    if errors:
        return True, errors
    return False, get_response(response)

# Initialize session state for checkboxes if not already done
if 'checkbox_states' not in st.session_state:
    st.session_state['checkbox_states'] = {
        "Hate": False,
        "Harassment": False,
        "Self-Harm": False,
        "Sexual": False,
        "Violence": False,
        "Toxicity" : False,
    }

def checkbox_changed(option):
    st.session_state['checkbox_states'][option] = not st.session_state['checkbox_states'][option]

# Sidebar with checkboxes
with st.sidebar:
    st.session_state['LLM'] = st.selectbox(
        "Select LLM Model",
        ("OpenAI", "AzureAI", "Anthropic", "Google")
    )
    st.sidebar.title("Apply Guardrails")
    for option in st.session_state['checkbox_states']:
        st.sidebar.checkbox(
            option,
            value=st.session_state['checkbox_states'][option],
            on_change=checkbox_changed,
            args=(option,)
        )
    topics_checkbox = st.sidebar.checkbox("Topics")
    if topics_checkbox:
        topics_value = st.text_input("Type Topics")
    else:
        topics_value = ""

    keyword_checkbox = st.sidebar.checkbox("Keywords")
    if keyword_checkbox:
        keyword_value = st.text_input("Type keywords seperated by commad")
    else:
        keyword_value = ""

# Chatbot UI
st.title("Hyperleap Guardrails Chatbot")
"""
I am a guardrails bot that detect and prevent harmful content.
"""

if prompt := st.chat_input():
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    st.session_state['messages'].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    error, response = process_response(prompt)
    if error:
        st.error(f'Potential {", ".join(response)} detected. Please rephrase your message.', icon="🚨")
    else:
        msg = response['choices'][0]['message']
        st.session_state['messages'].append(msg)
        st.chat_message("assistant").write(msg['content'])
